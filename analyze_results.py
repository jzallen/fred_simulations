#!/usr/bin/env python3
"""
FRED Simulation Data Analysis
This script analyzes the output from FRED simulations using pandas and matplotlib.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def load_data(file_name, data_dir="output/RUN1"):
    """Load FRED output data."""
    run_path = Path(data_dir)

    if not run_path.exists():
        print(f"Error: Run directory {data_dir} not found.")
        print("Make sure to run the FRED simulation first with: make run-fred")
        return None

    # Load main output data
    data_file = run_path / file_name

    if data_file.exists():
        data = pd.read_csv(data_file)
        print(f"Loaded: {len(data)} rows from {data_file.name}")
        return data
    else:
        print(f"Warning: {data_file} not found")
        return None


def analyze_population_data(data):
    """Analyze basic population statistics."""
    if data is None:
        return

    population_analysis_message = f"""
=== Population Analysis ===
Simulation period: {data['Date'].iloc[0]} to {data['Date'].iloc[-1]}
Population size: {data['Popsize'].iloc[0]:,}
Days simulated: {len(data)}
    """

    print(population_analysis_message)


def analyze_disease_data(data):
    """Analyze disease progression if available."""
    if data is None:
        print("No disease data available for analysis")
        return

    disease_analysis_message = f"""
=== Disease Analysis ===
Available columns: {data.columns.tolist()}
First few rows:
{data.head()}
    """
    print(disease_analysis_message)


def create_visualizations(out_data, influenza_data):
    """Create visualizations of the simulation results."""

    # Set up the plotting style
    plt.style.use("default")
    sns.set_palette("husl")

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle("FRED Simulation Analysis - Allegheny County, PA", fontsize=16)

    # Plot 1: Population over time
    def create_population_plot(ax, population_data):
        ax.plot(population_data["Day"], population_data["Popsize"], marker="o", linewidth=2)
        ax.set_title("Population Size Over Time")
        ax.set_xlabel("Day")
        ax.set_ylabel("Population")
        ax.ticklabel_format(style="plain", axis="y")
        ax.grid(True, alpha=0.3)

    # Plot 2: Disease data (if available)
    def create_disease_plot(ax, disease_data):
        # Plot available disease metrics
        numeric_cols = disease_data.select_dtypes(include=[np.number]).columns
        if "Day" in numeric_cols:
            numeric_cols = [col for col in numeric_cols if col != "Day"]

        if len(numeric_cols) > 0:
            for i, col in enumerate(numeric_cols[:3]):  # Plot up to 3 metrics
                if i < 3:
                    ax.plot(
                        (
                            disease_data["Day"]
                            if "Day" in disease_data.columns
                            else range(len(disease_data))
                        ),
                        disease_data[col],
                        marker="o",
                        label=col,
                    )
            ax.set_title("Disease Metrics Over Time")
            ax.set_xlabel("Day")
            ax.set_ylabel("Count")
            ax.legend()
            ax.grid(True, alpha=0.3)
        else:
            ax.text(
                0.5,
                0.5,
                "No numeric disease data\navailable for plotting",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_title("Disease Metrics")

    # Plot 3: Summary statistics
    def create_summary_plot(ax, population_data, disease_data):
        ax.axis("off")
        summary_text = "Simulation Summary\n\n"

        summary_text += f"Population: {population_data['Popsize'].iloc[0]:,}\n"
        summary_text += f"Days simulated: {len(population_data)}\n"
        summary_text += (
            f"Date range: {population_data['Date'].iloc[0]} to "
            f"{population_data['Date'].iloc[-1]}\n\n"
        )

        summary_text += f"Disease data points: {len(disease_data)}\n"
        summary_text += f"Disease metrics: {len(disease_data.columns)}\n"

        ax.text(
            0.1,
            0.9,
            summary_text,
            transform=ax.transAxes,
            fontsize=12,
            verticalalignment="top",
            fontfamily="monospace",
        )

    # Create all plots
    axes[0, 0].axis("off")  # Make the top-left subplot blank
    create_summary_plot(axes[0, 1], out_data, influenza_data)
    create_population_plot(axes[1, 0], out_data)
    create_disease_plot(axes[1, 1], influenza_data)

    plt.tight_layout()

    # Save the plot
    plt.savefig("fred_analysis.png", dpi=300, bbox_inches="tight")
    print("\n=== Visualization ===")
    print("Plot saved as 'fred_analysis.png'")

    # Show the plot if in interactive mode
    try:
        plt.show()
    except Exception:
        print("Plot created but not displayed (non-interactive environment)")


def main():
    """Main analysis function."""
    print("FRED Simulation Data Analysis")
    print("=" * 40)

    # Load data
    out_data = load_data(file_name="out.csv")
    influenza_data = load_data(file_name="Influenza.csv")

    if out_data is None and influenza_data is None:
        print("\nNo data found. Please run FRED simulation first:")
        print("  make run-fred")
        sys.exit(1)

    # Analyze data
    analyze_population_data(out_data)
    analyze_disease_data(influenza_data)

    # Create visualizations
    create_visualizations(out_data, influenza_data)

    print("\n=== Analysis Complete ===")
    print("Data analysis finished successfully!")


if __name__ == "__main__":
    main()
