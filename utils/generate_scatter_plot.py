"""
Generate a Nature-Style Scatter Plot

This script demonstrates how to generate a publication-quality scatter plot
in Nature journal style using the figure_generator module.
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Make sure the static/figures directory exists
os.makedirs('static/figures', exist_ok=True)

# Set up matplotlib backend
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Define the Nature style
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

# Nature colors
NATURE_COLORS = [
    '#3182bd',  # blue
    '#e6550d',  # orange
    '#31a354',  # green
    '#756bb1',  # purple
    '#636363',  # gray
]

def setup_nature_style():
    """Apply Nature journal style settings to matplotlib."""
    plt.style.use('default')  # Reset to default
    matplotlib.rcParams.update(NATURE_STYLE)

def create_figure(width=3.5, height=2.625):
    """Create a new figure with Nature-style settings."""
    setup_nature_style()
    fig, ax = plt.subplots(figsize=(width, height))
    return fig, ax

def scatter_plot(x_data, y_data, title=None, xlabel=None, ylabel=None, 
               color=None, label=None, filename=None, formats=None,
               marker='o', markersize=30, alpha=0.7, include_trend=False,
               fig_width=3.5, fig_height=2.625):
    """Create a scatter plot in Nature style."""
    fig, ax = create_figure(width=fig_width, height=fig_height)
    
    if color is None:
        color = NATURE_COLORS[0]
    
    ax.scatter(x_data, y_data, color=color, s=markersize, 
              alpha=alpha, marker=marker, label=label)
    
    if include_trend:
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        ax.plot(x_data, p(x_data), "--", color=NATURE_COLORS[1], 
                label=f'Trend: y={z[0]:.2f}x+{z[1]:.2f}')
    
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    
    if label or include_trend:
        ax.legend(loc='best', frameon=True, framealpha=0.8)
    
    ax.grid(True, linestyle='--', alpha=0.5, linewidth=0.5)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # Save figure if filename is provided
    if filename and formats:
        for fmt in formats:
            output_path = f'static/figures/{filename}.{fmt}'
            fig.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0.05)
    
    return fig, ax

def generate_correlation_example():
    """Generate an example scatter plot with a correlation."""
    print("Generating correlation scatter plot...")
    
    try:
        # Create sample data with a correlation
        np.random.seed(42)  # For reproducibility
        x = np.random.normal(0, 1, 50)
        y = 2 * x + 1 + np.random.normal(0, 0.5, 50)
        
        # Create a scatter plot with trend line
        fig, ax = scatter_plot(
            x, y, 
            title='Correlation Example',
            xlabel='Independent Variable',
            ylabel='Dependent Variable',
            label='Data Points',
            include_trend=True,
            filename='correlation_example',
            formats=['png', 'pdf']
        )
        
        print(f"Scatter plot saved to static/figures/correlation_example.png")
        return 'static/figures/correlation_example.png'
    except Exception as e:
        print(f"Error generating scatter plot: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_grouped_data_example():
    """Generate an example scatter plot with grouped data."""
    print("Generating grouped data scatter plot...")
    
    try:
        # Create sample data with groups
        np.random.seed(42)  # For reproducibility
        group1_x = np.random.normal(0, 0.5, 30)
        group1_y = np.random.normal(0, 0.5, 30)
        
        group2_x = np.random.normal(2, 0.5, 30)
        group2_y = np.random.normal(2, 0.5, 30)
        
        # Create figure and axes
        fig, ax = create_figure()
        
        # Plot each group
        ax.scatter(group1_x, group1_y, color=NATURE_COLORS[0], s=30, 
                  alpha=0.7, marker='o', label='Group 1')
        ax.scatter(group2_x, group2_y, color=NATURE_COLORS[1], s=30, 
                  alpha=0.7, marker='s', label='Group 2')
        
        ax.set_title('Grouped Data Example')
        ax.set_xlabel('X Variable')
        ax.set_ylabel('Y Variable')
        ax.legend(loc='best', frameon=True, framealpha=0.8)
        ax.grid(True, linestyle='--', alpha=0.5, linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        # Save the figure
        filename = 'grouped_data_example'
        for fmt in ['png', 'pdf']:
            output_path = f'static/figures/{filename}.{fmt}'
            fig.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0.05)
        
        print(f"Grouped scatter plot saved to static/figures/{filename}.png")
        return f'static/figures/{filename}.png'
    except Exception as e:
        print(f"Error generating grouped scatter plot: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Generate example scatter plots."""
    print("Generating example scatter plots in Nature style...")
    
    results = {}
    correlation_plot = generate_correlation_example()
    if correlation_plot:
        results['correlation'] = correlation_plot
    
    grouped_plot = generate_grouped_data_example()
    if grouped_plot:
        results['grouped'] = grouped_plot
    
    if results:
        print("\nAll scatter plots generated successfully!")
        print("\nTo include figures in your paper, use the following code:")
        
        if 'correlation' in results:
            print("\nFor correlation plot:")
            print('![Correlation Example](figures/correlation_example.png "Correlation Example")')
            
        if 'grouped' in results:
            print("\nFor grouped data plot:")
            print('![Grouped Data Example](figures/grouped_data_example.png "Grouped Data Example")')
    else:
        print("\nNo scatter plots were generated successfully.")
    
    return results

if __name__ == "__main__":
    main() 