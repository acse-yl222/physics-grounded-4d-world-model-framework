GRID_SIZE = 56
WINDOW_SIZE = 19
DT = 0.5
HIST_STEPS = 10
PRED_STEPS = 6
VEHICLE_DIM = 4  # [x, y, vx, vy]
REGULATION_DIM = 2  # speed_limit_ratio, signal_state
MAX_SPEED = 30.0
ROAD_LENGTH = 168.0  # Road length in meters (56 cells × 3 meters per cell)
CELL_SIZE = 3.0
DESTINATION_DIM = 2
TURN_ANGLE_DIM = 1
LANE_DIM = 2  # lane_center_row, lane_center_col
DRIVABLE_DIM = 1  # is_drivable
TOTAL_FEAT_DIM = (
    VEHICLE_DIM + REGULATION_DIM + DESTINATION_DIM + TURN_ANGLE_DIM + LANE_DIM + DRIVABLE_DIM
)  # = 12

INTERSECTION_CENTER = (28, 28)
ROAD_HALF_WIDTH = 2  # 2 cells × 3m = 6m per direction = 2 lanes, one cell per lane
SIGNAL_CYCLE = 60

ARRIVAL_RATE = 0.5  # traffic flow density
TURN_PROB_STRAIGHT = 0.50  # Steering Probability
TURN_PROB_LEFT = 0.30
TURN_PROB_RIGHT = 0.20
TURN_RADIUS_RIGHT = 6
TURN_RADIUS_LEFT = 9

HIDDEN_DIM = 256  # Dimension of MLP hidden layer
EGO_HIDDEN_DIM = 64  # Self-vehicle encoder output dimension
N_HIDDEN_LAYERS = 3  # Number of hidden layers in MLP
JACOBI_ITERS = 3
BATCH_SIZE = 64
LR = 1e-3
EPOCHS = 250
TRAIN_TRAJECTORIES = 2000
VAL_TRAJECTORIES = 200
EVAL_SEED_OFFSET = TRAIN_TRAJECTORIES + VAL_TRAJECTORIES
