"""
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

def scatter_plot(x_data, y_data, title=None, xlabel=None, ylabel=None, 
                color=None, label=None, filename=None, formats=None,
                marker='o', markersize=30, alpha=0.7, include_trend=False,
                fig_width=3.5, fig_height=2.625, z_data=None, 
                colormap='viridis', colorbar_label=None):
    """
    Create a scatter plot in Nature style.
    
    Args:
        x_data: List or array of x values
        y_data: List or array of y values
        title (str): Plot title
        xlabel (str): X-axis label
        ylabel (str): Y-axis label
        color: Color for points
        label (str): Label for legend
        filename (str): If provided, save the figure to this filename
        formats (list): List of formats to save as
        marker (str): Marker style
        markersize (float): Marker size
        alpha (float): Opacity of points
        include_trend (bool): If True, add trend line
        fig_width (float): Figure width in inches
        fig_height (float): Figure height in inches
        z_data: Optional array for coloring points
        colormap (str): Colormap if z_data is provided
        colorbar_label (str): Label for colorbar if z_data is provided
        
    Returns:
        tuple: (fig, ax) matplotlib objects
    """
    fig, ax = create_figure(width=fig_width, height=fig_height)
    
    if color is None and z_data is None:
        color = NATURE_COLORS[0]
    
    if z_data is not None:
        scatter = ax.scatter(x_data, y_data, c=z_data, cmap=colormap, 
                            s=markersize, alpha=alpha, marker=marker)
        cbar = plt.colorbar(scatter, ax=ax)
        if colorbar_label:
            cbar.set_label(colorbar_label)
    else:
        ax.scatter(x_data, y_data, color=color, s=markersize, 
                  alpha=alpha, marker=marker, label=label)
    
    if include_trend:
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        ax.plot(x_data, p(x_data), "--", color='#555555', 
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
    if filename:
        save_figure(fig, filename, formats=formats)
    
    return fig, ax

def figure_to_base64(fig, format='png', dpi=300):
    """
    Convert a matplotlib figure to base64 encoded string for embedding in HTML.
    
    Args:
        fig: Matplotlib figure object
        format (str): Image format (png, jpg, etc)
        dpi (int): Resolution
        
    Returns:
        str: Base64 encoded image string
    """
    buf = BytesIO()
    fig.savefig(buf, format=format, dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    import base64
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return f'data:image/{format};base64,{img_str}'
