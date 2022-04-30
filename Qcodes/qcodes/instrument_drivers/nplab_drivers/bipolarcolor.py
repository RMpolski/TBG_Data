from matplotlib.colors import LinearSegmentedColormap

# This is a list that maps values 0 to 1 into rgba colors
# The first number is the value that corresponds to the color
# The following tuple of 4 numbers corresponds to red, green, blue
# and alpha color channels (also 0 to 1).
# To make another colormap, you have to specify the 0 and 1 values and
# (if wanted) values in between

bipolarcolors = [(0, (0.0, 1.0, 1.0, 1.0)),
                 (0.25, (0.0, 0.1, 0.8, 1.0)),
                 (0.5, (0.05, 0.05, 0.05, 1.0)),
                 (0.75, (0.8, 0.1, 0.0, 1.0)),
                 (1, (1.0, 1.0, 0.0, 1.0))]

bipolar = LinearSegmentedColormap.from_list("bipolar", bipolarcolors)
