"""
Analysis module for extracting player reasoning and suspicion metrics from game logs.
"""

import json
import re
from typing import Dict, List, Any
from collections import defaultdict


def extract_reasoning_from_log(log) -> Dict[str, Any]:
    """Extract reasoning from an LM log."""
    if not log or not hasattr(log, 'result') or not log.result:
        return {}
    
    result = log.result
    reasoning = {}
    
    # Extract reasoning field if it exists
    if isinstance(result, dict):
        if 'reasoning' in result:
            reasoning['reasoning'] = result['reasoning']
        
        # Extract other relevant fields
        for key in ['say', 'vote', 'investigate', 'protect', 'remove', 'summary']:
            if key in result:
                reasoning[key] = result[key]
    
    return reasoning


def analyze_suspicion_from_text(text: str, player_name: str, all_players: List[str]) -> Dict[str, Any]:
    """
    Analyze a player's text to extract suspicion signals about other players.
    
    Returns a dict with:
    - mentioned_players: list of players mentioned
    - suspicious_of: list of players they seem suspicious of
    - trusts: list of players they seem to trust
    - sentiment: overall sentiment about each player
    """
    if not text:
        return {}
    
    text_lower = text.lower()
    analysis = {
        'mentioned_players': [],
        'suspicious_of': [],
        'trusts': [],
        'sentiment': {}
    }
    
    # Suspicion keywords
    suspicion_words = ['suspect', 'suspicious', 'doubt', 'werewolf', 'wolf', 
                      'lying', 'inconsistent', 'hiding', 'vote', 'remove', 
                      'eliminate', 'guilty', 'blame', 'accuse']
    
    # Trust keywords
    trust_words = ['trust', 'believe', 'innocent', 'villager', 'protect',
                   'save', 'ally', 'agree', 'honest', 'truthful']
    
    for player in all_players:
        if player == player_name:
            continue
            
        player_lower = player.lower()
        
        # Check if player is mentioned
        if player_lower in text_lower:
            analysis['mentioned_players'].append(player)
            
            # Find context around the player's name
            # Simple sentiment analysis based on nearby keywords
            suspicion_score = 0
            trust_score = 0
            
            for word in suspicion_words:
                # Check if suspicion word appears near this player's name
                pattern = f"{player_lower}.{{0,50}}{word}|{word}.{{0,50}}{player_lower}"
                if re.search(pattern, text_lower):
                    suspicion_score += 1
            
            for word in trust_words:
                pattern = f"{player_lower}.{{0,50}}{word}|{word}.{{0,50}}{player_lower}"
                if re.search(pattern, text_lower):
                    trust_score += 1
            
            # Categorize based on scores
            if suspicion_score > trust_score:
                analysis['suspicious_of'].append(player)
                analysis['sentiment'][player] = 'suspicious'
            elif trust_score > suspicion_score:
                analysis['trusts'].append(player)
                analysis['sentiment'][player] = 'trusting'
            elif suspicion_score > 0 or trust_score > 0:
                analysis['sentiment'][player] = 'neutral_mentioned'
    
    return analysis


def generate_suspicion_scorecard(state, logs) -> Dict[str, Any]:
    """
    Generate a comprehensive suspicion scorecard for all players.
    
    For each player, track:
    - What they know (their observations)
    - Who they've mentioned in debates
    - Who they seem suspicious of
    - Who they've voted for
    - Their reasoning for actions
    """
    
    scorecard = {}
    all_player_names = list(state.players.keys())
    
    for player_name, player in state.players.items():
        player_analysis = {
            'name': player_name,
            'role': player.role,
            'observations': player.observations,
            'mentioned_players': defaultdict(int),
            'suspicious_of': defaultdict(int),
            'trusts': defaultdict(int),
            'voted_for': [],
            'reasoning_history': [],
            'debate_contributions': []
        }
        
        # Analyze each round
        for round_idx, round_log in enumerate(logs):
            round_data = {
                'round': round_idx,
                'actions': {}
            }
            
            # Analyze bidding reasoning
            for bid_turn in round_log.bid:
                for bid_player, bid_log in bid_turn:
                    if bid_player == player_name:
                        reasoning = extract_reasoning_from_log(bid_log)
                        if reasoning:
                            round_data['actions']['bid'] = reasoning
            
            # Analyze debate contributions
            for debate_player, debate_log in round_log.debate:
                if debate_player == player_name:
                    reasoning = extract_reasoning_from_log(debate_log)
                    if reasoning:
                        player_analysis['debate_contributions'].append({
                            'round': round_idx,
                            'reasoning': reasoning.get('reasoning', ''),
                            'said': reasoning.get('say', '')
                        })
                        round_data['actions']['debate'] = reasoning
                        
                        # Analyze suspicion from what they said
                        said_text = reasoning.get('say', '')
                        suspicion_analysis = analyze_suspicion_from_text(
                            said_text, player_name, all_player_names
                        )
                        
                        # Update counters
                        for mentioned in suspicion_analysis.get('mentioned_players', []):
                            player_analysis['mentioned_players'][mentioned] += 1
                        for suspicious in suspicion_analysis.get('suspicious_of', []):
                            player_analysis['suspicious_of'][suspicious] += 1
                        for trusted in suspicion_analysis.get('trusts', []):
                            player_analysis['trusts'][trusted] += 1
            
            # Analyze votes
            for vote_log in round_log.votes:
                for vote in vote_log:
                    if vote.player == player_name:
                        reasoning = extract_reasoning_from_log(vote.log)
                        if reasoning:
                            player_analysis['voted_for'].append({
                                'round': round_idx,
                                'voted_for': vote.voted_for,
                                'reasoning': reasoning.get('reasoning', '')
                            })
                            round_data['actions']['vote'] = {
                                'target': vote.voted_for,
                                'reasoning': reasoning
                            }
            
            # Analyze summaries
            for summary_player, summary_log in round_log.summaries:
                if summary_player == player_name:
                    reasoning = extract_reasoning_from_log(summary_log)
                    if reasoning:
                        round_data['actions']['summary'] = reasoning
                        
                        # Analyze suspicion from summary
                        summary_text = reasoning.get('reasoning', '') + ' ' + reasoning.get('summary', '')
                        suspicion_analysis = analyze_suspicion_from_text(
                            summary_text, player_name, all_player_names
                        )
                        
                        for mentioned in suspicion_analysis.get('mentioned_players', []):
                            player_analysis['mentioned_players'][mentioned] += 1
                        for suspicious in suspicion_analysis.get('suspicious_of', []):
                            player_analysis['suspicious_of'][suspicious] += 1
                        for trusted in suspicion_analysis.get('trusts', []):
                            player_analysis['trusts'][trusted] += 1
            
            if round_data['actions']:
                player_analysis['reasoning_history'].append(round_data)
        
        # Convert defaultdicts to regular dicts for JSON serialization
        player_analysis['mentioned_players'] = dict(player_analysis['mentioned_players'])
        player_analysis['suspicious_of'] = dict(player_analysis['suspicious_of'])
        player_analysis['trusts'] = dict(player_analysis['trusts'])
        
        scorecard[player_name] = player_analysis
    
    return scorecard


def calculate_influence_score(logs: List[Any], player_name: str, all_players: List[str]) -> float:
    """
    Calculate the influence score for a player based on game logs.

    Influence score is determined by:
    - Number of times the player's suggestions (e.g., votes, accusations) are followed.
    - Alignment between the player's actions and the overall game outcome.

    Returns a float representing the influence score.
    """
    influence_score = 0
    total_actions = 0

    for log in logs:
        if not hasattr(log, 'result') or not log.result:
            continue

        result = log.result

        # Check if the player made suggestions (e.g., votes, accusations)
        if 'vote' in result and result['vote'] == player_name:
            total_actions += 1
            # Check if others followed the vote
            if 'votes' in result:
                followers = [voter for voter, target in result['votes'].items() if target == player_name]
                influence_score += len(followers)

        # Additional metrics can be added here (e.g., alignment with outcomes)

    return influence_score / total_actions if total_actions > 0 else 0.0


def calculate_internal_scorecards(logs: List[Any], all_players: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Calculate internal scorecards for each player, where each player rates others on a sliding scale.

    Returns a dictionary where:
    - Keys are player names.
    - Values are dictionaries mapping other players to their scores.
    """
    scorecards = {player: {other: 0.0 for other in all_players if other != player} for player in all_players}

    for log in logs:
        if not hasattr(log, 'result') or not log.result:
            continue

        result = log.result

        # Example: Extract suspicion or trust signals from logs
        for player in all_players:
            if player in result:
                for other_player, score in result[player].get('ratings', {}).items():
                    if other_player in scorecards[player]:
                        scorecards[player][other_player] += score

    return scorecards


def calculate_suspicion_scores(logs: List[Any], all_players: List[str]) -> Dict[str, float]:
    """
    Calculate percentage-wise suspicion scores for each player.

    Returns a dictionary where:
    - Keys are player names.
    - Values are suspicion scores (0.0 to 1.0).
    """
    suspicion_counts = {player: 0 for player in all_players}
    total_mentions = {player: 0 for player in all_players}

    for log in logs:
        if not hasattr(log, 'result') or not log.result:
            continue

        result = log.result

        # Analyze suspicion signals in the log
        for player in all_players:
            if player in result:
                if 'suspicious_of' in result[player]:
                    for suspicious_player in result[player]['suspicious_of']:
                        if suspicious_player in suspicion_counts:
                            suspicion_counts[suspicious_player] += 1
                total_mentions[player] += 1

    # Calculate percentage-wise suspicion scores
    suspicion_scores = {}
    for player in all_players:
        if total_mentions[player] > 0:
            suspicion_scores[player] = suspicion_counts[player] / total_mentions[player]
        else:
            suspicion_scores[player] = 0.0

    return suspicion_scores


def save_analysis(state, logs, directory: str):
    """Save analysis and suspicion scorecard to a file."""
    scorecard = generate_suspicion_scorecard(state, logs)
    
    # Create a summary
    summary = {
        'game_info': {
            'session_id': state.session_id,
            'winner': state.winner,
            'total_rounds': len(state.rounds),
            'players': {
                name: player.role 
                for name, player in state.players.items()
            }
        },
        'suspicion_scorecard': scorecard,
        'analysis_notes': {
            'description': 'This file contains reasoning analysis for each player',
            'suspicion_scorecard_explanation': {
                'mentioned_players': 'Count of how many times this player mentioned each other player',
                'suspicious_of': 'Count of times this player expressed suspicion toward each player',
                'trusts': 'Count of times this player expressed trust toward each player',
                'voted_for': 'History of who they voted for and why',
                'debate_contributions': 'What they said in debates with reasoning',
                'reasoning_history': 'Round-by-round breakdown of all their reasoning'
            }
        }
    }
    
    analysis_file = f"{directory}/analysis_metrics.json"
    with open(analysis_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Analysis metrics saved to: {analysis_file}")
    
    return analysis_file

