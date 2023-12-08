# Imports
import numpy as np
import math
import pybullet as p

# Constants
R = np.diag([0.1, 0.1])  # Measurement noise covariance
dt = 0.1 # Seconds
linear_V_limit = 0.1 # m/s
angular_W_limit = 0.01 # rad/s

# Public Functions
def simulate_sensor_reading(actual_position):
    # Systematic Error
    systematic_error = calculate_systematic_error()

    # Random Error
    random_error = generate_random_error()

    # Environmental Factors (optional, based on your project's complexity)
    environmental_error = calculate_environmental_error()

    # Combine errors with the actual position
    noisy_position = actual_position + random_error

    return noisy_position

def calculate_systematic_error():
    # This function calculates any constant or predictable errors
    systematic_error_value = None
    # This could be based on calibration data or known sensor biases
    return systematic_error_value

def generate_random_error():
    # Generate random noise, possibly using a Gaussian distribution
    # You can use sensor_noise_params to set the mean and standard deviation

    # Generate noise with 0 mean and R cov
    random_error_value = np.random.multivariate_normal([0, 0], R)
    return random_error_value

def calculate_environmental_error(environmental_factors):
    # If applicable, calculate errors based on environmental factors
    environmental_error_value = None
    # This could include temperature, humidity, electromagnetic interference, etc.
    return environmental_error_value




def motion_planner_model(current_position, target_position):
    # Position: (x,y,theta)
    # Return linear and angular velocity of the robot
    delta_position = (target_position - current_position)
    omega = (math.atan2(delta_position[1], delta_position[0]) + delta_position[2])/dt
    v = np.sqrt(delta_position[0]**2 + delta_position[1]**2)/dt

    return v,omega

def motion_planner(current_position, target_position):

    """ From a start position, it gives the control inputs and positions along the trajectory to the destination.
    To calculate it, it uses RTR method, which stands for Rotate-Translate-Rotate
    R: Rotate from current state to go to the destination position.
    T: Translate to the destination position.
    R: Once reached, rotate on the spot to point to the desination orientation.

    Returns the trajectory of points and the action states
    """

    trajectory = np.empty((0, 3))
    actions = np.empty((0, 2))

    # Rotate on the spot: "R"-T-R
    print("ROTATING")
    current_state = current_position
    angle_to_rotate = math.atan2(target_position[1]-current_position[1],target_position[0]-current_position[0]) - current_position[2]
    end_state = np.array([current_position[0],current_position[1],angle_to_rotate])
    trajectory = np.vstack((trajectory,current_state))
    while (np.linalg.norm(current_state-end_state)> 0.01):
        u = velocity_model(current_state,end_state)
        u[0] = 0
        # True state update
        A = np.eye(3)
        B = np.array([[math.cos(current_state[2]), 0],
                        [math.sin(current_state[2]), 0],
                        [0, 1]])
        next_state = A @ current_state + B @ u
        trajectory = np.vstack((trajectory,next_state))
        actions = np.vstack((actions,u))
        current_state = next_state
    
    
    # Translate towards the destination: R-"T"-R
    print("TRANSLATING")
    end_state = np.array([target_position[0],target_position[1],current_state[2]])
    while (np.linalg.norm(current_state-end_state)> 0.02):
        u = velocity_model(current_state,end_state)
        u[1] = 0

        # True state update
        A = np.eye(3)
        B = np.array([[math.cos(current_state[2]), 0],
                        [math.sin(current_state[2]), 0],
                        [0, 1]])
        next_state = A @ current_state + B @ u
        trajectory = np.vstack((trajectory,next_state))
        actions = np.vstack((actions,u))
        current_state = next_state

    
    # Rotate on the spot: R-T-"R"
    print("ROTATING")
    angle_to_rotate = target_position[2] - current_state[2]
    end_state = target_position
    while (np.linalg.norm(current_state-end_state)> 0.02):
        u = velocity_model(current_state,end_state)
        u[0] = 0

        # True state update
        A = np.eye(3)
        B = np.array([[math.cos(current_state[2]), 0],
                        [math.sin(current_state[2]), 0],
                        [0, 1]])
        next_state = A @ current_state + B @ u
        trajectory = np.vstack((trajectory,next_state))
        actions = np.vstack((actions,u))
        current_state = next_state
    
    
    # print(trajectory)
    # print(actions)
    return trajectory, actions

def velocity_model(omega_R,oomega_L):
    wheel_radius = 0.1
    wheel_base = 0.7
    v = wheel_radius * (omega_R+oomega_L)
    w = wheel_radius * (omega_R-oomega_L)/wheel_base
    return [v,w]

def get_omegas(robot_id):
    l_wheel_idx = 6
    r_wheel_idx = 7

    l_wheel_state = p.getJointState(robot_id,l_wheel_idx)
    r_wheel_state = p.getJointState(robot_id,r_wheel_idx)

    omega_l = l_wheel_state[1]
    omega_r = r_wheel_state[1]

    return omega_l,omega_r


    # PASS current_position and target_position
    # Calculate the linear and angular velocity of the robot
    # v,omega = motion_planner_model(current_position,target_position)
    # v_limited = np.clip(v,-linear_V_limit,linear_V_limit)
    # omega_limited = np.clip(omega,-angular_W_limit,angular_W_limit)

    # # Control Input to the robot
    # u = np.array([v_limited, omega_limited])
    # return u

def predict_next_state(current_state,dt,v,omega):
    """
    current_state: current position and orientation of the robot 
                    (x,y,theta)
    dt: small change in time/step
    v: linear velocity
    omega: angular velocity"""
    # measured_pos,measured_= getMeasuredPosition(robot)

    x,y,theta = current_state
    d_theta = omega*dt
    theta_new = theta + d_theta
    if abs(omega) < 1e-6:
            omega = 1e-6
            d_x = v*dt*np.cos(theta)
            d_y = v*dt*np.sin(theta)
    else:
        # when the robot is turning
        d_x = (v/omega)*(np.sin(theta_new)-np.sin(theta))
        d_y = (v/omega)*(-np.cos(theta_new)+np.cos(theta))

    theta_new = (theta_new + np.pi) % (2 * np.pi) - np.pi
    x_new = d_x + x
    y_new = d_y + y

    next_state = np.array([x_new,y_new,theta_new])

    return next_state

# def calculate_std(robot,previous_pose):
#     measured_pos,measured_ori = getMeasuredPosition(robot)

#     k1 = 0.01
#     k2 = 0.1
#     k3 = 0.001
#     k4 = 0.0002
#     dx = measured_pos[0] - previous_pose[0]
#     dy = measured_pos[1] - previous_pose[1]
#     dt = measured_ori - previous_pose[2]

#     alpha = angle_diff(np.arctan2(dy,dx),previous_pose[2])

#     direction = 1
#     # when the robot is oriented toward the next state
#     if(abs(alpha)>np.pi/2):
#         alpha = angle_diff(np.pi,alpha)
#         direction = -1

#     beta = angle_diff(dt,alpha)
#     dist = direction*np.sqrt(dx**2 + dy**2)

#     # check if the robot has moved
#     if(abs(dist)>0.001 or (abs(dt)>0.001)):
#         if(abs(dist)>0.005):
#             has_moved = True
#         if(abs(dt)>0.003):
#             has_rot = True

#     rot1_std = k1 * abs(alpha) + k3*abs(dist)
#     trans_std = k2 * abs(dist) + k3*abs(alpha) + k4 *abs(beta)
#     rot2_std = k1 * abs(beta) + k3*abs(dist)

#     return rot1_std,rot2_std,trans_std

# START HERE
def getMeasuredPosition(robot):
    pos,ori = p.getBasePositionAndOrientation(robot)
    noisy_pos = np.array(pos)[:2] + np.random.normal(0, 1, 2)
    noisy_ori = np.array(ori)[2] + np.random.normal(0, 1, 1)
    return np.concatenate((noisy_pos,noisy_ori))


def angle_diff(ori1,ori2):
    diff = ori1-ori2

    while (diff > np.pi):
        diff-=2*np.pi
    
    while (diff< -np.pi):
        diff+=2*np.pi

    return diff