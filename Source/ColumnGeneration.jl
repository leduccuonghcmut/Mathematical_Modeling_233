using JuMP
import DataFrames
import HiGHS
import Plots
import SparseArrays
import Test  #src

struct Piece
    w::Float64
    d::Int
end

struct Data
    pieces::Vector{Piece}
    W::Float64
end

function Base.show(io::IO, d::Data)
    println(io, "Data for the cutting stock problem:")
    println(io, "  W = $(d.W)")
    println(io, "with pieces:")
    println(io, "   i   w_i d_i")
    println(io, "  ------------")
    for (i, p) in enumerate(d.pieces)
        println(io, lpad(i, 4), " ", lpad(p.w, 5), " ", lpad(p.d, 3))
    end
    return
end

function get_data()
    data = [
        75.0 38
        75.0 44
        75.0 30
        75.0 41
        75.0 36
        53.8 33
        53.0 36
        51.0 41
        50.2 35
        32.2 37
        30.8 44
        29.8 49
        20.1 37
        16.2 36
        14.5 42
        11.0 33
        8.6 47
        8.2 35
        6.6 49
        5.1 42
    ]
    return Data([Piece(data[i, 1], data[i, 2]) for i in axes(data, 1)], 100.0)
end

data = get_data()

I = length(data.pieces)
J = 1_000  # Some large number
# model = Model(HiGHS.Optimizer)
# set_silent(model)
# @variable(model, x[1:I, 1:J] >= 0, Int)
# @variable(model, y[1:J], Bin)
# @objective(model, Min, sum(y))
# @constraint(model, [i in 1:I], sum(x[i, :]) >= data.pieces[i].d)
# @constraint(
#     model,
#     [j in 1:J],
#     sum(data.pieces[i].w * x[i, j] for i in 1:I) <= data.W * y[j],
# );


# set_time_limit_sec(model, 5.0)
# optimize!(model)
# solution_summary(model)

patterns = map(1:I) do i
    n_pieces = floor(Int, data.W / data.pieces[i].w)
    return SparseArrays.sparsevec([i], [n_pieces], I)
end

# println(patterns)

# for visualization purpose
function cutting_locations(data::Data, pattern::SparseArrays.SparseVector)
    locations = Float64[]
    offset = 0.0
    for (i, c) in zip(SparseArrays.findnz(pattern)...)
        for _ in 1:c
            offset += data.pieces[i].w
            push!(locations, offset)
        end
    end
    return locations
end

function plot_patterns(data::Data, patterns)
    plot = Plots.bar(;
        xlims = (0, length(patterns) + 1),
        ylims = (0, data.W),
        xlabel = "Pattern",
        ylabel = "Chiều dài mảnh nguyên liệu",
    )
    for (i, p) in enumerate(patterns)
        locations = cutting_locations(data, p)
        Plots.bar!(
            plot,
            fill(i, length(locations)),
            reverse(locations);
            bar_width = 0.6,
            label = false,
            # change color to pink
            color = :pink,
        )
    end
    return plot
end

# plot_patterns(data, patterns)

# setup model 
model = Model(HiGHS.Optimizer)
# to avoid unnecessary output
set_silent(model)
# define variables
@variable(model, x[1:length(patterns)] >= 0, Int)
@objective(model, Min, sum(x))
@constraint(model, demand[i in 1:I], patterns[i]' * x >= data.pieces[i].d)
optimize!(model)
@assert is_solved_and_feasible(model)
# in kết quả ra console 
# solution_summary(model)

unset_integer.(x)
optimize!(model)
@assert is_solved_and_feasible(model; dual = true)
# calculate dual value from 1 to 20
dual_values = dual.(demand)
# for i in 1:20
#     println("Dual value for demand[$i]: ", dual_values[i])
# end


function solve_pricing(data::Data, π::Vector{Float64})
    # Get the number of items
    I = length(π)
    # Create a new optimization model using the HiGHS optimizer
    model = Model(HiGHS.Optimizer)
    # Set the model to run silently (without output)
    set_silent(model)
    # Define integer decision variables y[i] for each item, constrained to be non-negative
    @variable(model, y[1:I] >= 0, Int)
    # Add a constraint: the total weight of selected items must not exceed the capacity W
    @constraint(model, sum(data.pieces[i].w * y[i] for i in 1:I) <= data.W)
    # Define the objective function
    @objective(model, Max, sum(π[i] * y[i] for i in 1:I))
    optimize!(model)
    @assert is_solved_and_feasible(model)
    number_of_rolls_saved = objective_value(model)
    # Check if the benefit of the pattern is more than the cost of a new roll plus some tolerance
    if number_of_rolls_saved > 1 + 1e-8
        return SparseArrays.sparse(round.(Int, value.(y)))
    end
    # If the benefit is not sufficient
    return nothing
end


while true
    ## Solve the linear relaxation
    optimize!(model)
    @assert is_solved_and_feasible(model; dual = true)
    ## Obtain a new dual vector
    π = dual.(demand)
    ## Solve the pricing problem
    new_pattern = solve_pricing(data, π)
    ## Stop iterating if there is no new pattern
    if new_pattern === nothing
        @info "No new patterns, terminating the algorithm."
        break
    end
    push!(patterns, new_pattern)
    ## Create a new column
    push!(x, @variable(model, lower_bound = 0))
    ## Update the objective coefficient of the new column
    set_objective_coefficient(model, x[end], 1.0)
    ## Update the non-zeros in the coefficient matrix
    for (i, count) in zip(SparseArrays.findnz(new_pattern)...)
        set_normalized_coefficient(demand[i], x[end], count)
    end
    println("Found new pattern. Total patterns = $(length(patterns))")
end

# # show pattern 30
# println("patterns[30] : \n", patterns[30])

# plot_patterns(data, patterns)
solution = DataFrames.DataFrame([
    (pattern = p, rolls = value(x_p)) for (p, x_p) in enumerate(x)
])
filter!(row -> row.rolls > 0, solution)

Test.@test sum(ceil.(Int, solution.rolls)) == 341  #src
sum(ceil.(Int, solution.rolls))

# Alternatively, we can re-introduce the integrality constraints and resolve the
# problem:

set_integer.(x)
optimize!(model)
@assert is_solved_and_feasible(model)
solution = DataFrames.DataFrame([
    (pattern = p, rolls = value(x_p)) for (p, x_p) in enumerate(x)
])
filter!(row -> row.rolls > 0, solution)

# This now requires 334 rolls:
print(solution)
Test.@test isapprox(sum(solution.rolls), 334; atol = 1e-6)  #src
sum(solution.rolls)
