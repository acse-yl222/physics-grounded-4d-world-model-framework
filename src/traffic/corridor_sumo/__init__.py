"""SUMO traffic pipeline for Overture-derived city networks (imperial_corridor scene).

Overture road segments -> SUMO plain XML -> netconvert -> demand (TfL buses from a
cached download, synthetic randomTrips cars/taxis/buses) -> headless SUMO with FCD
output -> protocol v1.1 sparse trajectories and a compact viewer binary.
"""
