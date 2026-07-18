from execution.pyramiding import PyramidingManager



manager = PyramidingManager()



add = manager.should_add_position(
    position_count=1,
    entry_price=64000,
    current_price=72000
)



size = manager.calculate_new_size(
    2
)



print("==============================")
print("PYRAMIDING TEST")
print("==============================")


print("Add Position:", add)

print("New Size:", size)