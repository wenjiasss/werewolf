import os
import matplotlib.pyplot as plt
import seaborn as sns

def plot_beliefs_over_time(beliefs_over_time, output_dir):
    """
    Plot average belief distribution per player per round.

    :param beliefs_over_time: Dict[int, Dict[str, Dict[str, float]]] - Beliefs per round per player.
    :param output_dir: str - Directory to save the plot.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    for round_num, player_beliefs in beliefs_over_time.items():
        plt.figure(figsize=(10, 6))
        for player, beliefs in player_beliefs.items():
            roles = list(beliefs.keys())
            confidences = list(beliefs.values())
            plt.plot(roles, confidences, marker='o', label=player)

        plt.title(f"Belief Distribution - Round {round_num}")
        plt.xlabel("Roles")
        plt.ylabel("Confidence")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"beliefs_round_{round_num}.png"))
        plt.close()

def plot_metric(metric_values, metric_name, output_dir):
    """
    Plot a generic metric over time.

    :param metric_values: Dict[int, float] - Metric values per round.
    :param metric_name: str - Name of the metric.
    :param output_dir: str - Directory to save the plot.
    """
    os.makedirs(output_dir, exist_ok=True)

    rounds = list(metric_values.keys())
    values = list(metric_values.values())

    plt.figure(figsize=(10, 6))
    plt.plot(rounds, values, marker='o')
    plt.title(f"{metric_name} Over Time")
    plt.xlabel("Round")
    plt.ylabel(metric_name)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{metric_name.lower().replace(' ', '_')}_over_time.png"))
    plt.close()

def save_visualizations(log_directory, beliefs_over_time, metrics):
    """
    Save all visualizations to the log directory.

    :param log_directory: str - Directory to save the visualizations.
    :param beliefs_over_time: Dict[int, Dict[str, Dict[str, float]]] - Beliefs per round per player.
    :param metrics: Dict[str, Dict[int, float]] - Metrics per round.
    """
    belief_dir = os.path.join(log_directory, "beliefs")
    metrics_dir = os.path.join(log_directory, "metrics")

    plot_beliefs_over_time(beliefs_over_time, belief_dir)

    for metric_name, metric_values in metrics.items():
        plot_metric(metric_values, metric_name, metrics_dir)