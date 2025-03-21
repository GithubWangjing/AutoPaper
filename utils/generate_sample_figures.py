"""
Generate Sample Figures

This script generates sample figures using the figure_generator module,
following the Nature journal style. Run this script to generate sample figures
that can be included in academic papers.
"""

import os
import sys
import traceback
import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create the static/figures directory if it doesn't exist
try:
    os.makedirs('static/figures', exist_ok=True)
    print(f"Created directory: static/figures")
except Exception as e:
    print(f"Error creating directory: {e}")
    traceback.print_exc()

# First create a minimal figure generator module with core functionality
try:
    print("Creating figure_generator.py module...")
    with open('utils/figure_generator.py', 'w') as f:
        f.write('''"""
Figure Generator for Academic Papers

This module provides utilities to create publication-quality figures in Nature journal style.
It offers functions to generate common scientific visualizations with appropriate styling.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import os
from matplotlib.ticker import MaxNLocator
from io import BytesIO

# Nature style settings
NATURE_STYLE = {
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 8,
    'axes.labelsize': 8,
    'axes.titlesize': 8,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'figure.titlesize': 10,
    'figure.figsize': (3.5, 2.625),  # Nature column width
    'figure.dpi': 300,
    'axes.linewidth': 0.5,
    'lines.linewidth': 1,
    'axes.labelpad': 4,
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'xtick.major.size': 3,
    'ytick.major.size': 3,
    'axes.spines.right': True,
    'axes.spines.top': True,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
    'axes.formatter.use_mathtext': True,
    'axes.autolimit_mode': 'round_numbers'
}

# Nature color palette - based on commonly used colors in Nature publications
NATURE_COLORS = [
    '#3182bd',  # blue
    '#e6550d',  # orange
    '#31a354',  # green
    '#756bb1',  # purple
    '#636363',  # gray
    '#6baed6',  # light blue
    '#fd8d3c',  # light orange
    '#74c476',  # light green
    '#9e9ac8',  # light purple
    '#969696',  # light gray
]

def setup_nature_style():
    """Apply Nature journal style settings to matplotlib."""
    plt.style.use('default')  # Reset to default
    mpl.rcParams.update(NATURE_STYLE)
    
def create_figure(width=3.5, height=2.625):
    """
    Create a new figure with Nature-style settings.
    
    Args:
        width (float): Width in inches. Default is 3.5 (Nature single column).
        height (float): Height in inches. Default is 2.625 (3:4 ratio).
        
    Returns:
        tuple: A tuple containing (figure, axis)
    """
    setup_nature_style()
    fig, ax = plt.subplots(figsize=(width, height))
    return fig, ax

def save_figure(fig, filename, dpi=300, formats=None):
    """
    Save figure in specified formats.
    
    Args:
        fig: Matplotlib figure object
        filename (str): Output filename without extension
        dpi (int): Resolution in dots per inch
        formats (list): List of formats to save as (e.g., ['png', 'pdf', 'svg'])
    
    Returns:
        list: Paths to saved files
    """
    if formats is None:
        formats = ['png', 'pdf']
        
    saved_files = []
    
    # Create directory if it doesn't exist
    os.makedirs('static/figures', exist_ok=True)
    
    for fmt in formats:
        output_path = f'static/figures/{filename}.{fmt}'
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight', pad_inches=0.05)
        saved_files.append(output_path)
    
    return saved_files

def line_plot(x_data, y_data, title=None, xlabel=None, ylabel=None, 
              colors=None, labels=None, filename=None, formats=None,
              legend_loc='best', marker='o', markersize=4, linewidth=1,
              include_grid=True, fig_width=3.5, fig_height=2.625):
    """
    Create a line plot in Nature style.
    
    Args:
        x_data: List or array of x values, or list of lists for multiple lines
        y_data: List or array of y values, or list of lists for multiple lines
        title (str): Plot title
        xlabel (str): X-axis label
        ylabel (str): Y-axis label
        colors (list): List of colors for lines
        labels (list): List of labels for legend
        filename (str): If provided, save the figure to this filename
        formats (list): List of formats to save as
        legend_loc (str): Legend location
        marker (str): Marker style
        markersize (float): Marker size
        linewidth (float): Line width
        include_grid (bool): Whether to include grid lines
        fig_width (float): Figure width in inches
        fig_height (float): Figure height in inches
        
    Returns:
        tuple: (fig, ax) matplotlib objects
    """
    fig, ax = create_figure(width=fig_width, height=fig_height)
    
    # Determine if we have multiple lines
    multi_line = isinstance(y_data[0], (list, np.ndarray))
    
    if colors is None:
        colors = NATURE_COLORS
    
    if multi_line:
        for i, y in enumerate(y_data):
            color = colors[i % len(colors)]
            label = labels[i] if labels and i < len(labels) else f"Series {i+1}"
            x = x_data[i] if isinstance(x_data[0], (list, np.ndarray)) else x_data
            ax.plot(x, y, marker=marker, markersize=markersize, 
                    linewidth=linewidth, color=color, label=label)
    else:
        ax.plot(x_data, y_data, marker=marker, markersize=markersize,
                linewidth=linewidth, color=colors[0], 
                label=labels[0] if labels else None)
    
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    
    # Add legend if we have labels
    if (labels and multi_line) or (labels and not multi_line and labels[0]):
        ax.legend(loc=legend_loc, frameon=True, framealpha=0.8)
    
    if include_grid:
        ax.grid(True, linestyle='--', alpha=0.7, linewidth=0.5)
    
    # Integer ticks if the data range is small
    if len(np.unique(np.round(x_data if not multi_line else x_data[0]))) <= 10:
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # Save figure if filename is provided
    if filename:
        save_figure(fig, filename, formats=formats)
    
    return fig, ax

def bar_plot(categories, values, title=None, xlabel=None, ylabel=None, 
             color=None, filename=None, formats=None, 
             fig_width=3.5, fig_height=2.625, horizontal=False,
             error_bars=None):
    """
    Create a bar plot in Nature style.
    
    Args:
        categories: List of category names
        values: List of values
        title (str): Plot title
        xlabel (str): X-axis label
        ylabel (str): Y-axis label
        color (str): Bar color
        filename (str): If provided, save the figure to this filename
        formats (list): List of formats to save as
        fig_width (float): Figure width in inches
        fig_height (float): Figure height in inches
        horizontal (bool): If True, create horizontal bars
        error_bars (list): List of error values for error bars
        
    Returns:
        tuple: (fig, ax) matplotlib objects
    """
    fig, ax = create_figure(width=fig_width, height=fig_height)
    
    if color is None:
        color = NATURE_COLORS[0]
    
    x = np.arange(len(categories))
    
    if horizontal:
        bars = ax.barh(x, values, color=color, height=0.6, alpha=0.8, 
                       xerr=error_bars, capsize=3)
        ax.set_yticks(x)
        ax.set_yticklabels(categories)
    else:
        bars = ax.bar(x, values, color=color, width=0.6, alpha=0.8, 
                      yerr=error_bars, capsize=3)
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
    
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # Save figure if filename is provided
    if filename:
        save_figure(fig, filename, formats=formats)
    
    return fig, ax
''')
    print("Successfully created figure_generator.py module")
except Exception as e:
    print(f"Error creating figure_generator.py: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("Setting up matplotlib...")
    # Set up matplotlib
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    print("Successfully set up matplotlib")
    
    # Import the functions directly
    print("Importing functions directly...")
    
    # Define the functions here directly
    def setup_nature_style():
        """Apply Nature journal style settings to matplotlib."""
        plt.style.use('default')  # Reset to default
        NATURE_STYLE = {
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
            'font.size': 8,
            'axes.labelsize': 8,
            'axes.titlesize': 8,
            'xtick.labelsize': 7,
            'ytick.labelsize': 7,
            'legend.fontsize': 7,
            'figure.titlesize': 10,
            'figure.figsize': (3.5, 2.625),  # Nature column width
            'figure.dpi': 300,
            'axes.linewidth': 0.5,
            'lines.linewidth': 1,
            'axes.labelpad': 4,
            'xtick.major.width': 0.5,
            'ytick.major.width': 0.5,
            'xtick.major.size': 3,
            'ytick.major.size': 3,
            'axes.spines.right': True,
            'axes.spines.top': True,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.05,
            'axes.formatter.use_mathtext': True,
            'axes.autolimit_mode': 'round_numbers'
        }
        matplotlib.rcParams.update(NATURE_STYLE)
        
    def create_figure(width=3.5, height=2.625):
        """Create a new figure with Nature-style settings."""
        setup_nature_style()
        fig, ax = plt.subplots(figsize=(width, height))
        return fig, ax

    def save_figure(fig, filename, dpi=300, formats=None):
        """Save figure in specified formats."""
        if formats is None:
            formats = ['png', 'pdf']
            
        saved_files = []
        
        # Create directory if it doesn't exist
        os.makedirs('static/figures', exist_ok=True)
        
        for fmt in formats:
            output_path = f'static/figures/{filename}.{fmt}'
            fig.savefig(output_path, dpi=dpi, bbox_inches='tight', pad_inches=0.05)
            saved_files.append(output_path)
        
        return saved_files

    def line_plot(x_data, y_data, title=None, xlabel=None, ylabel=None, 
                colors=None, labels=None, filename=None, formats=None,
                legend_loc='best', marker='o', markersize=4, linewidth=1,
                include_grid=True, fig_width=3.5, fig_height=2.625):
        """Create a line plot in Nature style."""
        fig, ax = create_figure(width=fig_width, height=fig_height)
        
        # Nature color palette
        NATURE_COLORS = [
            '#3182bd',  # blue
            '#e6550d',  # orange
            '#31a354',  # green
            '#756bb1',  # purple
            '#636363',  # gray
            '#6baed6',  # light blue
            '#fd8d3c',  # light orange
            '#74c476',  # light green
            '#9e9ac8',  # light purple
            '#969696',  # light gray
        ]
        
        # Determine if we have multiple lines
        multi_line = isinstance(y_data[0], (list, np.ndarray))
        
        if colors is None:
            colors = NATURE_COLORS
        
        if multi_line:
            for i, y in enumerate(y_data):
                color = colors[i % len(colors)]
                label = labels[i] if labels and i < len(labels) else f"Series {i+1}"
                x = x_data[i] if isinstance(x_data[0], (list, np.ndarray)) else x_data
                ax.plot(x, y, marker=marker, markersize=markersize, 
                        linewidth=linewidth, color=color, label=label)
        else:
            ax.plot(x_data, y_data, marker=marker, markersize=markersize,
                    linewidth=linewidth, color=colors[0], 
                    label=labels[0] if labels else None)
        
        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)
        
        # Add legend if we have labels
        if (labels and multi_line) or (labels and not multi_line and labels[0]):
            ax.legend(loc=legend_loc, frameon=True, framealpha=0.8)
        
        if include_grid:
            ax.grid(True, linestyle='--', alpha=0.7, linewidth=0.5)
        
        # Integer ticks if the data range is small
        if len(np.unique(np.round(x_data if not multi_line else x_data[0]))) <= 10:
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        # Save figure if filename is provided
        if filename:
            save_figure(fig, filename, formats=formats)
        
        return fig, ax

    def bar_plot(categories, values, title=None, xlabel=None, ylabel=None, 
                color=None, filename=None, formats=None, 
                fig_width=3.5, fig_height=2.625, horizontal=False,
                error_bars=None):
        """Create a bar plot in Nature style."""
        fig, ax = create_figure(width=fig_width, height=fig_height)
        
        # Nature color palette
        NATURE_COLORS = [
            '#3182bd',  # blue
            '#e6550d',  # orange
            '#31a354',  # green
            '#756bb1',  # purple
            '#636363',  # gray
        ]
        
        if color is None:
            color = NATURE_COLORS[0]
        
        x = np.arange(len(categories))
        
        if horizontal:
            bars = ax.barh(x, values, color=color, height=0.6, alpha=0.8, 
                        xerr=error_bars, capsize=3)
            ax.set_yticks(x)
            ax.set_yticklabels(categories)
        else:
            bars = ax.bar(x, values, color=color, width=0.6, alpha=0.8, 
                        yerr=error_bars, capsize=3)
            ax.set_xticks(x)
            ax.set_xticklabels(categories)
        
        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        # Save figure if filename is provided
        if filename:
            save_figure(fig, filename, formats=formats)
        
        return fig, ax
    
    print("Successfully set up figure generation functions")
except Exception as e:
    print(f"Error setting up matplotlib: {e}")
    traceback.print_exc()
    sys.exit(1)

def generate_example_line_plot():
    """Generate an example line plot."""
    print("Generating example line plot...")
    
    try:
        # Generate sample data
        x = np.linspace(0, 10, 20)
        y1 = np.sin(x)
        y2 = np.cos(x)
        
        # Create a line plot with two series
        fig, ax = line_plot(
            [x, x], [y1, y2], 
            title='Trigonometric Functions',
            xlabel='Time (s)',
            ylabel='Amplitude',
            labels=['sin(x)', 'cos(x)'],
            filename='example_line_plot',
            formats=['png']
        )
        
        print(f"Line plot saved to static/figures/example_line_plot.png")
        plt.close(fig)  # Close the figure to free memory
        return 'static/figures/example_line_plot.png'
    except Exception as e:
        print(f"Error generating line plot: {e}")
        traceback.print_exc()
        return None

def generate_example_bar_plot():
    """Generate an example bar plot."""
    print("Generating example bar plot...")
    
    try:
        # Sample data
        categories = ['A', 'B', 'C', 'D', 'E']
        values = [3.5, 2.8, 4.2, 1.9, 3.2]
        error_bars = [0.2, 0.3, 0.4, 0.1, 0.3]
        
        # Create a bar plot
        fig, ax = bar_plot(
            categories, values,
            title='Sample Measurements',
            xlabel='Sample Category',
            ylabel='Value (units)',
            error_bars=error_bars,
            filename='example_bar_plot',
            formats=['png']
        )
        
        print(f"Bar plot saved to static/figures/example_bar_plot.png")
        plt.close(fig)  # Close the figure to free memory
        return 'static/figures/example_bar_plot.png'
    except Exception as e:
        print(f"Error generating bar plot: {e}")
        traceback.print_exc()
        return None

def generate_example_horizontal_bar_plot():
    """Generate an example horizontal bar plot."""
    print("Generating example horizontal bar plot...")
    
    try:
        # Sample data for publication metrics
        journals = ['Nature', 'Science', 'Cell', 'PNAS', 'PLoS One']
        impact_factors = [49.96, 47.73, 41.58, 11.47, 3.24]
        
        # Create a horizontal bar plot
        fig, ax = bar_plot(
            journals, impact_factors,
            title='Journal Impact Factors (2022)',
            xlabel='Impact Factor',
            ylabel='Journal',
            horizontal=True,  # Make it horizontal
            filename='journal_impact_factors',
            formats=['png']
        )
        
        print(f"Horizontal bar plot saved to static/figures/journal_impact_factors.png")
        plt.close(fig)  # Close the figure to free memory
        return 'static/figures/journal_impact_factors.png'
    except Exception as e:
        print(f"Error generating horizontal bar plot: {e}")
        traceback.print_exc()
        return None

def main():
    """Generate all example figures."""
    print("Generating example figures in Nature style...")
    
    # Make sure the output directory exists
    os.makedirs('static/figures', exist_ok=True)
    
    # Generate example figures
    results = {}
    line_plot_path = generate_example_line_plot()
    if line_plot_path:
        results['line_plot'] = line_plot_path
        
    bar_plot_path = generate_example_bar_plot()
    if bar_plot_path:
        results['bar_plot'] = bar_plot_path
        
    horizontal_bar_path = generate_example_horizontal_bar_plot()
    if horizontal_bar_path:
        results['horizontal_bar'] = horizontal_bar_path
    
    if results:
        print("\nAll figures generated successfully!")
        print("\nTo include figures in your paper, use the following code:")
        
        if 'line_plot' in results:
            print("\nFor line plot:")
            print('![Trigonometric Functions](figures/example_line_plot.png "Trigonometric Functions")')
        
        if 'bar_plot' in results:
            print("\nFor bar plot:")
            print('![Sample Measurements](figures/example_bar_plot.png "Sample Measurements")')
        
        if 'horizontal_bar' in results:
            print("\nFor horizontal bar plot:")
            print('![Journal Impact Factors](figures/journal_impact_factors.png "Journal Impact Factors")')
    else:
        print("\nNo figures were generated successfully.")
    
    return results

if __name__ == "__main__":
    main() 