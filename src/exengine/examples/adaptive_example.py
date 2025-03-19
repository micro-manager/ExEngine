"""
Adaptive Microscopy Example

This script demonstrates automated microscopy techniques for finding and focusing on samples
using the simulated microscope provided by the OpenWavefrontShaping backend.

1. Autofocus: Finds the optimal Z position by maximizing image sharpness
2. Sample Centering: Locates the brightest region of the sample in XY using different search strategies

The script creates a simulated microscope with a sparse random sample, intentionally defocuses 
and offsets it, then demonstrates the recovery of optimal focus and position using different 
algorithms. Two search strategies are implemented for XY centering:
- Grid search: Systematic but slow scan of XY positions
- Gradient ascent: Efficient local optimization following brightness gradient

The results are visualized showing the initial (defocused, offset) image, 
the focused but offset image, and the final focused and centered image.
"""

import numpy as np

import openwfs
from openwfs.simulation import Camera, StaticSource
from openwfs.processors import SingleRoi
from exengine.kernel.executor import ExecutionEngine

from openwfs.plot_utilities import imshow
from openwfs.simulation import StaticSource, Microscope, XYStage, Stage
import astropy.units as u
from exengine import ExecutionEngine
from exengine.backends.openwfs import CameraSchema

import matplotlib.pyplot as plt


# construct a microscope with a random image
img = (np.random.rand(100, 100) > 0.99) * 1.0
pixel_size = 0.1 * u.micrometer

specimen = StaticSource(img, pixel_size=pixel_size)
xy_stage = XYStage(0.1 * u.micrometer, 0.1 * u.micrometer)
z_stage = Stage("z", 0.1 * u.micrometer)
microscope = Microscope(specimen, wavelength=0.5 * u.micrometer, numerical_aperture=0.8, xy_stage=xy_stage, z_stage=z_stage)
engine = ExecutionEngine()
camera = engine.register("camera", microscope, schema=CameraSchema)

def capture_image():
    camera.arm() # does nothing, OpenWFS camera is always armed
    camera.start()
    frame, metadata = camera.pop_data()
    return frame


def calculate_sharpness(image):
    return np.var(image)

def autofocus(microscope, camera, z_range=(-40, 40), step_size=1):
    """
    Finds optimal focus by scanning through Z positions and maximizing image sharpness.
    
    Args:
        microscope: Microscope object with controllable z_stage
        camera: Camera object for image acquisition
        z_range (tuple): Range of Z positions to scan in micrometers (min, max)
        step_size (float): Step size between Z positions in micrometers
    
    Returns:
        float: Optimal Z position offset in micrometers relative to starting position
    
    The function uses image variance as a sharpness metric, scanning through the specified
    Z range and returning to the position with maximum sharpness.
    """
    # Store initial position
    initial_position = microscope.z_stage.position
    
    # Create array of z positions to test
    z_positions = np.arange(z_range[0], z_range[1] + step_size, step_size)
    sharpness_values = []
    
    # Capture images and calculate sharpness at each z position
    for z in z_positions:
        # Move to new position
        microscope.z_stage.position = initial_position + z * u.micrometer
        
        # Capture and analyze image
        frame = capture_image()
        sharpness_values.append(calculate_sharpness(frame))
    
    # Find position with maximum sharpness
    best_z = z_positions[np.argmax(sharpness_values)]

    # plot the sharpness values
    # plt.figure(figsize=(5, 5))
    # plt.plot(z_positions, sharpness_values)
    # plt.show()
    
    # Move to best position
    microscope.z_stage.position = initial_position + best_z * u.micrometer
    
    return best_z

def calculate_brightness(image):
    return np.sum(image)

def center_sample(microscope, camera, xy_range=(-20, 20), step_size=2):
    """
    Centers the sample using an exhaustive grid search strategy.
    
    Args:
        microscope: Microscope object with controllable xy_stage
        camera: Camera object for image acquisition
        xy_range (tuple): Range of XY positions to scan in micrometers (min, max)
        step_size (float): Step size between positions in micrometers
    
    Returns:
        tuple: (best_x, best_y) optimal position offsets in micrometers
    
    Performs a systematic grid search over the specified XY range, measuring
    total image brightness at each position. While thorough, this method can
    be slow for large search areas or fine step sizes.
    """
    # Store initial position
    initial_x = microscope.xy_stage.x
    initial_y = microscope.xy_stage.y
    
    # Create array of positions to test
    positions = np.arange(xy_range[0], xy_range[1] + step_size, step_size)
    brightness_values = np.zeros((len(positions), len(positions)))
    
    # Scan in XY and calculate brightness at each position
    for i, x in enumerate(positions):
        for j, y in enumerate(positions):
            # Move to new position
            microscope.xy_stage.x = initial_x + x * u.micrometer
            microscope.xy_stage.y = initial_y + y * u.micrometer
            
            # Capture and analyze image
            frame = capture_image()
            brightness_values[i, j] = calculate_brightness(frame)
    
    # Find position with maximum brightness
    max_idx = np.unravel_index(np.argmax(brightness_values), brightness_values.shape)
    best_x = positions[max_idx[0]]
    best_y = positions[max_idx[1]]
    
    # Move to best position
    microscope.xy_stage.x = initial_x + best_x * u.micrometer
    microscope.xy_stage.y = initial_y + best_y * u.micrometer
    
    return best_x, best_y

def center_sample_gradient(microscope, camera, step_size=2, max_steps=20, tolerance=0.01):
    """
    Centers the sample using gradient ascent optimization.
    
    Args:
        microscope: Microscope object with controllable xy_stage
        camera: Camera object for image acquisition
        step_size (float): Initial step size in micrometers
        max_steps (int): Maximum number of optimization steps
        tolerance (float): Relative improvement threshold for step size reduction
    
    Returns:
        tuple: (best_x, best_y) optimal position offsets in micrometers
    
    Uses an adaptive gradient ascent approach:
    1. Tests brightness in four directions around current position
    2. Moves in direction of highest brightness
    3. Reduces step size when improvements become small
    4. Stops when step size becomes too small or max steps reached
    
    More efficient than grid search for smooth brightness landscapes,
    but may get trapped in local maxima.
    """
    initial_x = microscope.xy_stage.x
    initial_y = microscope.xy_stage.y
    
    current_brightness = calculate_brightness(capture_image())
    step = step_size
    
    for _ in range(max_steps):
        # Test brightness in all four directions
        positions = [
            (step, 0),  # right
            (-step, 0), # left
            (0, step),  # up
            (0, -step)  # down
        ]
        
        brightness_values = []
        for dx, dy in positions:
            microscope.xy_stage.x = initial_x + dx * u.micrometer
            microscope.xy_stage.y = initial_y + dy * u.micrometer
            brightness_values.append(calculate_brightness(capture_image()))
            
        # Return to center
        microscope.xy_stage.x = initial_x
        microscope.xy_stage.y = initial_y
        
        # Find best direction
        best_idx = np.argmax(brightness_values)
        best_brightness = brightness_values[best_idx]
        
        # If improvement is minimal, reduce step size
        if (best_brightness - current_brightness) / current_brightness < tolerance:
            step *= 0.5
            if step < 0.1:  # Minimum step size
                break
            continue
            
        # Move in best direction
        dx, dy = positions[best_idx]
        initial_x += dx * u.micrometer
        initial_y += dy * u.micrometer
        microscope.xy_stage.x = initial_x
        microscope.xy_stage.y = initial_y
        current_brightness = best_brightness
    
    return (initial_x - microscope.xy_stage.x).to(u.micrometer).value, \
           (initial_y - microscope.xy_stage.y).to(u.micrometer).value


# Move half FOV away in both X and Y
microscope.xy_stage.x = microscope.xy_stage.x + img.shape[0] * pixel_size * 0.5
microscope.xy_stage.y = microscope.xy_stage.y + img.shape[1] * pixel_size * 0.5

# introduce initial defocus
microscope.z_stage.position = microscope.z_stage.position + 20 * u.micrometer

# capture and display initial image
initial_frame = capture_image()

# Run autofocus
best_z_position = autofocus(microscope, camera)
print(f"Best focus found at z-offset: {best_z_position} micrometers")
focused_frame = capture_image()

# Run centering
# best_x, best_y = center_sample(microscope, camera)  # Grid search
best_x, best_y = center_sample_gradient(microscope, camera)  # Gradient ascent
# best_x, best_y = center_sample_coarse_to_fine(microscope, camera)  # Coarse-to-fine
final_frame = capture_image()

# plot the initial and final images
fig, ax = plt.subplots(1, 3, figsize=(15, 5))
ax[0].imshow(initial_frame)
ax[0].set_title('Initial')
ax[1].imshow(focused_frame)
ax[1].set_title('Focused')
ax[2].imshow(final_frame)
ax[2].set_title('Final')
plt.show(block=True)

engine.shutdown()
