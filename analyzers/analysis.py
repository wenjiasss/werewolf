import json
import re
import os
import csv
from typing import Dict, List, Any
from collections import defaultdict


# Extracts reasoning from an LM log
def extract_reasoning_from_log(log) -> Dict[str, Any]:
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


# Extracts role assessment data from logs
def extract_role_assessments(state, logs) -> Dict[str, Any]:
    all_assessments = {}
    all_player_names = list(state.players.keys())
    
    for player_name in all_player_names:
        player_assessments = {
            'player': player_name,
            'true_role': state.players[player_name].role,
            'by_round': []
        }
        
        # Analyze each round
        for round_idx, round_log in enumerate(logs):
            round_assessments = {
                'round': round_idx,
                'post_night_assessment': None,
                'debate_turn_assessments': []
            }
            
            # Extract post-night assessment
            for assess_player, assess_log in round_log.role_assessments_post_night:
                if assess_player == player_name:
                    result = extract_reasoning_from_log(assess_log)
                    round_assessments['post_night_assessment'] = result
                    break
            
            # Extract assessments during debate
            for turn_idx, turn_assessments in enumerate(round_log.role_assessments_during_debate):
                for assess_player, assess_log in turn_assessments:
                    if assess_player == player_name:
                        result = extract_reasoning_from_log(assess_log)
                        round_assessments['debate_turn_assessments'].append({
                            'turn': turn_idx,
                            'assessment': result
                        })
                        break
            
            player_assessments['by_round'].append(round_assessments)
        
        all_assessments[player_name] = player_assessments
    
    return all_assessments


# Generates a comprehensive scorecard for all players
def generate_suspicion_scorecard(state, logs) -> Dict[str, Any]:
    scorecard = {}
    all_player_names = list(state.players.keys())
    
    for player_name, player in state.players.items():
        player_analysis = {
            'name': player_name,
            'role': player.role,
            'observations': player.observations,
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
            
            if round_data['actions']:
                player_analysis['reasoning_history'].append(round_data)
        
        scorecard[player_name] = player_analysis
    
    # Add role assessment data
    role_assessments = extract_role_assessments(state, logs)
    
    return {
        'player_scorecard': scorecard,
        'role_assessments': role_assessments
    }


# Exports per-round CSV files with player metrics
def export_round_csvs(state, logs, scorecard_data, directory: str):
    all_player_names = list(state.players.keys())
    total_rounds = len(state.rounds)
    
    for round_idx in range(total_rounds):
        round_dir = f"{directory}/round_{round_idx}"
        os.makedirs(round_dir, exist_ok=True)
        
        round_state = state.rounds[round_idx]
        
        # 1. Main player metrics CSV
        metrics_file = f"{round_dir}/player_metrics.csv"
        with open(metrics_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'player', 'true_role', 'alive', 'eliminated', 'exiled', 
                'voted_for', 'spoke_in_debate', 'debate_contribution'
            ])
            
            for player_name in all_player_names:
                player = state.players[player_name]
                scorecard = scorecard_data['player_scorecard'].get(player_name, {})
                
                alive = player_name in round_state.players
                eliminated = round_state.eliminated == player_name
                exiled = round_state.exiled == player_name
                
                # Get vote for this round
                voted_for = ''
                for vote_data in scorecard.get('voted_for', []):
                    if vote_data.get('round') == round_idx:
                        voted_for = vote_data.get('voted_for', '')
                
                # Check if they spoke in debate
                spoke = any(speaker == player_name for speaker, _ in round_state.debate)
                debate_text = ''
                for speaker, dialogue in round_state.debate:
                    if speaker == player_name:
                        debate_text = dialogue[:100] + '...' if len(dialogue) > 100 else dialogue
                        break
                
                writer.writerow([
                    player_name,
                    player.role,
                    'Yes' if alive else 'No',
                    'Yes' if eliminated else 'No',
                    'Yes' if exiled else 'No',
                    voted_for,
                    'Yes' if spoke else 'No',
                    debate_text
                ])
        
        # 2. Role assessments - Post night
        post_night_file = f"{round_dir}/role_assessments_post_night.csv"
        with open(post_night_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'assessor', 'assessor_true_role', 'target_player', 'target_true_role',
                'suspected_role', 'confidence', 'correct'
            ])
            
            for player_name in all_player_names:
                if player_name not in round_state.players:
                    continue  # Skip dead players
                    
                assessments = scorecard_data['role_assessments'].get(player_name, {})
                round_data = assessments.get('by_round', [])[round_idx] if round_idx < len(assessments.get('by_round', [])) else None
                
                if round_data and round_data.get('post_night_assessment'):
                    assessment_data = round_data['post_night_assessment']
                    for assessment in assessment_data.get('assessments', []):
                        target = assessment.get('player')
                        suspected = assessment.get('suspected_role')
                        confidence = assessment.get('confidence')
                        
                        if target and target in state.players:
                            target_true_role = state.players[target].role
                            # Simplify role comparison (Seer/Doctor count as Villager for assessment purposes)
                            target_simplified = 'Villager' if target_true_role in ['Villager', 'Seer', 'Doctor'] else 'Werewolf'
                            correct = 'Yes' if suspected == target_simplified else 'No'
                            
                            writer.writerow([
                                player_name,
                                state.players[player_name].role,
                                target,
                                target_true_role,
                                suspected,
                                confidence,
                                correct
                            ])
        
        # 3. Role assessments - During debate (one CSV per debate turn)
        for turn_idx, turn_assessments in enumerate(round_state.role_assessments_during_debate):
            debate_assess_file = f"{round_dir}/role_assessments_debate_turn_{turn_idx}.csv"
            with open(debate_assess_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'assessor', 'assessor_true_role', 'target_player', 'target_true_role',
                    'suspected_role', 'confidence', 'correct', 'speaker_this_turn'
                ])
                
                speaker_this_turn = round_state.debate[turn_idx][0] if turn_idx < len(round_state.debate) else ''
                
                for player_name, assessment_result in turn_assessments.items():
                    for assessment in assessment_result.get('assessments', []):
                        target = assessment.get('player')
                        suspected = assessment.get('suspected_role')
                        confidence = assessment.get('confidence')
                        
                        if target and target in state.players:
                            target_true_role = state.players[target].role
                            target_simplified = 'Villager' if target_true_role in ['Villager', 'Seer', 'Doctor'] else 'Werewolf'
                            correct = 'Yes' if suspected == target_simplified else 'No'
                            
                            writer.writerow([
                                player_name,
                                state.players[player_name].role,
                                target,
                                target_true_role,
                                suspected,
                                confidence,
                                correct,
                                speaker_this_turn
                            ])
    
        # 4. Confidence evolution tracking - simplified to just post_night data
        evolution_file = f"{round_dir}/confidence_evolution.csv"
        with open(evolution_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Simplified header - just post_night data
            header = ['assessor', 'assessor_role', 'target', 'target_role', 'suspected_role', 
                     'post_night_confidence', 'post_night_correct']
            
            writer.writerow(header)
            
            # Build evolution data for each assessor-target pair
            evolution_data = {}
            
            # First, get post-night assessments
            for player_name in all_player_names:
                if player_name not in round_state.players:
                    continue
                
                assessments = scorecard_data['role_assessments'].get(player_name, {})
                round_data = assessments.get('by_round', [])[round_idx] if round_idx < len(assessments.get('by_round', [])) else None
                
                if round_data and round_data.get('post_night_assessment'):
                    assessment_data = round_data['post_night_assessment']
                    for assessment in assessment_data.get('assessments', []):
                        target = assessment.get('player')
                        if target and target in state.players:
                            key = (player_name, target)
                            suspected = assessment.get('suspected_role')
                            confidence = assessment.get('confidence')
                            target_true_role = state.players[target].role
                            target_simplified = 'Villager' if target_true_role in ['Villager', 'Seer', 'Doctor'] else 'Werewolf'
                            correct = suspected == target_simplified
                            
                            evolution_data[key] = {
                                'assessor_role': state.players[player_name].role,
                                'target_role': target_true_role,
                                'suspected_role': suspected,
                                'post_night_confidence': confidence,
                                'post_night_correct': correct,
                                'debate_turns': []
                            }
            
            # Add debate turn assessments
            for turn_idx, turn_assessments in enumerate(round_state.role_assessments_during_debate):
                for player_name, assessment_result in turn_assessments.items():
                    for assessment in assessment_result.get('assessments', []):
                        target = assessment.get('player')
                        if target and target in state.players:
                            key = (player_name, target)
                            suspected = assessment.get('suspected_role')
                            confidence = assessment.get('confidence')
                            target_true_role = state.players[target].role
                            target_simplified = 'Villager' if target_true_role in ['Villager', 'Seer', 'Doctor'] else 'Werewolf'
                            correct = suspected == target_simplified
                            
                            if key not in evolution_data:
                                # First assessment for this pair (no post-night data)
                                evolution_data[key] = {
                                    'assessor_role': state.players[player_name].role,
                                    'target_role': target_true_role,
                                    'suspected_role': suspected,
                                    'post_night_confidence': '',
                                    'post_night_correct': '',
                                    'debate_turns': []
                                }
                            
                            evolution_data[key]['debate_turns'].append({
                                'confidence': confidence,
                                'correct': correct,
                                'turn': turn_idx
                            })
            
            # Write rows - only post_night data
            for (assessor, target), data in sorted(evolution_data.items()):
                row = [
                    assessor,
                    data['assessor_role'],
                    target,
                    data['target_role'],
                    data['suspected_role'],
                    data['post_night_confidence'],
                    'Yes' if data['post_night_correct'] else 'No' if data['post_night_correct'] != '' else ''
                ]
                
                writer.writerow(row)
        
        # 5. Dialogue context file - shows what was said
        dialogue_file = f"{round_dir}/debate_dialogue.csv"
        with open(dialogue_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['dialogue'])
            
            for turn_idx, (speaker, dialogue) in enumerate(round_state.debate):
                writer.writerow([dialogue])
        
        # 6. Signed confidence scores - final assessment scaled by correctness
        signed_conf_file = f"{round_dir}/signed_confidence_scores.csv"
        with open(signed_conf_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'assessor', 'assessor_role', 'target', 'target_role',
                'final_suspected_role', 'final_confidence', 'correct',
                'signed_confidence_score', 'interpretation'
            ])
            
            # Get final assessments (last debate turn)
            if round_state.role_assessments_during_debate:
                final_turn = round_state.role_assessments_during_debate[-1]
                
                for player_name, assessment_result in final_turn.items():
                    assessor_role = state.players[player_name].role if player_name in state.players else 'Unknown'
                    
                    for assessment in assessment_result.get('assessments', []):
                        target = assessment.get('player')
                        suspected = assessment.get('suspected_role')
                        confidence = assessment.get('confidence', 0)
                        
                        if target and target in state.players:
                            target_true_role = state.players[target].role
                            target_simplified = 'Villager' if target_true_role in ['Villager', 'Seer', 'Doctor'] else 'Werewolf'
                            
                            # Calculate signed confidence score
                            correct = suspected == target_simplified
                            sign = 1 if correct else -1
                            signed_score = sign * confidence
                            
                            # Interpretation
                            if signed_score > 50:
                                interpretation = "High confidence, CORRECT"
                            elif signed_score > 0:
                                interpretation = "Low confidence, correct"
                            elif signed_score > -50:
                                interpretation = "Low confidence, wrong"
                            else:
                                interpretation = "High confidence, WRONG"
                            
                            writer.writerow([
                                player_name,
                                assessor_role,
                                target,
                                target_true_role,
                                suspected,
                                confidence,
                                'Yes' if correct else 'No',
                                signed_score,
                                interpretation
                            ])
        
        # 7. Internal consistency - do players vote for who they think is most suspicious?
        consistency_file = f"{round_dir}/internal_consistency.csv"
        with open(consistency_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'player', 'player_role', 
                'top_suspect', 'top_suspect_confidence', 'top_suspect_role',
                'actual_vote', 'actual_vote_role',
                'consistent', 'consistency_type'
            ])
            
            # Get final assessments and votes for this round
            if round_state.role_assessments_during_debate and round_state.votes:
                final_turn = round_state.role_assessments_during_debate[-1]
                final_votes = round_state.votes[-1]  # Last vote of the round
                
                for player_name, assessment_result in final_turn.items():
                    # Find who they thought was most suspicious (highest confidence werewolf)
                    werewolf_assessments = []
                    for assessment in assessment_result.get('assessments', []):
                        target = assessment.get('player')
                        suspected = assessment.get('suspected_role')
                        confidence = assessment.get('confidence', 0)
                        
                        if target and target in state.players and suspected == 'Werewolf':
                            werewolf_assessments.append({
                                'target': target,
                                'confidence': confidence,
                                'role': state.players[target].role
                            })
                    
                    # Find their top suspect (highest confidence werewolf assessment)
                    top_suspect = None
                    top_confidence = 0
                    top_suspect_role = None
                    
                    if werewolf_assessments:
                        # Sort by confidence and take highest
                        werewolf_assessments.sort(key=lambda x: x['confidence'], reverse=True)
                        top = werewolf_assessments[0]
                        top_suspect = top['target']
                        top_confidence = top['confidence']
                        top_suspect_role = top['role']
                    
                    # Get their actual vote
                    actual_vote = final_votes.get(player_name, '')
                    actual_vote_role = state.players[actual_vote].role if actual_vote and actual_vote in state.players else ''
                    
                    # Determine consistency
                    consistent = 'N/A'
                    consistency_type = 'N/A'
                    
                    if not top_suspect:
                        top_suspect = 'N/A'
                        consistency_type = 'No werewolf suspects'
                    elif not actual_vote:
                        consistency_type = 'No vote recorded'
                    elif top_suspect == actual_vote:
                        consistent = 'Yes'
                        consistency_type = 'Consistent'
                    else:
                        consistent = 'No'
                        consistency_type = 'Inconsistent'
                    
                    player_role = state.players[player_name].role if player_name in state.players else 'Unknown'
                    
                    writer.writerow([
                        player_name,
                        player_role,
                        top_suspect,
                        top_confidence if top_suspect != 'N/A' else '',
                        top_suspect_role if top_suspect_role else '',
                        actual_vote if actual_vote else 'None',
                        actual_vote_role if actual_vote_role else '',
                        consistent,
                        consistency_type
                    ])
    
    print(f"Exported CSV files for {total_rounds} rounds to {directory}/round_*/")
    
    # Create cross-round consistency summary
    consistency_summary_file = f"{directory}/consistency_summary.csv"
    with open(consistency_summary_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'player', 'true_role', 'total_rounds_voted', 
            'consistent_votes', 'inconsistent_votes', 'consistency_rate',
            'avg_top_suspect_confidence', 'notes'
        ])
        
        # Aggregate consistency across all rounds
        player_consistency = {}
        
        for round_idx, round_state in enumerate(state.rounds):
            # Read the consistency data we just generated
            if round_state.role_assessments_during_debate and round_state.votes:
                final_turn = round_state.role_assessments_during_debate[-1]
                final_votes = round_state.votes[-1]
                
                for player_name, assessment_result in final_turn.items():
                    if player_name not in player_consistency:
                        player_consistency[player_name] = {
                            'consistent': 0,
                            'inconsistent': 0,
                            'total': 0,
                            'confidences': []
                        }
                    
                    # Find top suspect
                    werewolf_assessments = []
                    for assessment in assessment_result.get('assessments', []):
                        target = assessment.get('player')
                        suspected = assessment.get('suspected_role')
                        confidence = assessment.get('confidence', 0)
                        
                        if target and target in state.players and suspected == 'Werewolf':
                            werewolf_assessments.append({
                                'target': target,
                                'confidence': confidence
                            })
                    
                    if werewolf_assessments:
                        werewolf_assessments.sort(key=lambda x: x['confidence'], reverse=True)
                        top = werewolf_assessments[0]
                        top_suspect = top['target']
                        top_confidence = top['confidence']
                        
                        player_consistency[player_name]['confidences'].append(top_confidence)
                        
                        actual_vote = final_votes.get(player_name)
                        if actual_vote:
                            player_consistency[player_name]['total'] += 1
                            if top_suspect == actual_vote:
                                player_consistency[player_name]['consistent'] += 1
                            else:
                                player_consistency[player_name]['inconsistent'] += 1
        
        # Write summary
        for player_name in sorted(player_consistency.keys()):
            data = player_consistency[player_name]
            player_role = state.players[player_name].role if player_name in state.players else 'Unknown'
            
            total = data['total']
            consistent = data['consistent']
            inconsistent = data['inconsistent']
            consistency_rate = (consistent / total * 100) if total > 0 else 0
            
            avg_confidence = sum(data['confidences']) / len(data['confidences']) if data['confidences'] else 0
            
            # Notes based on patterns
            notes = []
            if consistency_rate == 100:
                notes.append('Always votes for top suspect')
            elif consistency_rate == 0:
                notes.append('Never votes for top suspect')
            elif consistency_rate >= 75:
                notes.append('Usually consistent')
            elif consistency_rate <= 25:
                notes.append('Usually inconsistent')
            
            if avg_confidence >= 80:
                notes.append('high confidence in suspects')
            elif avg_confidence <= 40:
                notes.append('low confidence in suspects')
            
            writer.writerow([
                player_name,
                player_role,
                total,
                consistent,
                inconsistent,
                f"{consistency_rate:.1f}%",
                f"{avg_confidence:.1f}",
                '; '.join(notes) if notes else ''
            ])
    
    print(f"Exported consistency summary to {consistency_summary_file}")
    
    # Create belief influence summary per round
    for round_idx, round_state in enumerate(state.rounds):
        round_dir = f"{directory}/round_{round_idx}"
        
        # Calculate belief shifts caused by each speaker
        influence_file = f"{round_dir}/belief_influence.csv"
        with open(influence_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'speaker', 'speaker_role', 
                'total_belief_shift', 'num_assessors_influenced',
                'most_influenced_player'
            ])
            
            # For each debate turn, calculate shifts
            for turn_idx in range(len(round_state.role_assessments_during_debate)):
                if turn_idx >= len(round_state.debate):
                    continue
                    
                speaker_name = round_state.debate[turn_idx][0]
                speaker_role = state.players[speaker_name].role if speaker_name in state.players else 'Unknown'
                
                # Get before assessments (from previous turn or post-night)
                if turn_idx == 0:
                    # Compare to post-night assessments
                    before_assessments = {}
                    assessments_data = scorecard_data['role_assessments']
                    for player_name in all_player_names:
                        if player_name not in round_state.players:
                            continue
                        player_data = assessments_data.get(player_name, {})
                        round_data = player_data.get('by_round', [])[round_idx] if round_idx < len(player_data.get('by_round', [])) else None
                        if round_data and round_data.get('post_night_assessment'):
                            before_assessments[player_name] = round_data['post_night_assessment'].get('assessments', [])
                else:
                    # Compare to previous debate turn
                    before_assessments = round_state.role_assessments_during_debate[turn_idx - 1]
                
                # Get after assessments (this turn)
                after_assessments = round_state.role_assessments_during_debate[turn_idx]
                
                # Calculate shifts for each assessor
                total_shift = 0
                assessor_shifts = {}
                
                for assessor_name, after_data in after_assessments.items():
                    if assessor_name == speaker_name:
                        continue  # Don't count self-shifts
                    
                    # Get before data
                    if turn_idx == 0:
                        before_list = before_assessments.get(assessor_name, [])
                    else:
                        before_data = before_assessments.get(assessor_name, {})
                        before_list = before_data.get('assessments', [])
                    
                    after_list = after_data.get('assessments', [])
                    
                    # Convert to dicts for easier lookup
                    before_dict = {}
                    for assessment in before_list:
                        target = assessment.get('player')
                        if target and target in state.players:
                            suspected = assessment.get('suspected_role')
                            confidence = assessment.get('confidence', 0)
                            # Convert to signed score: Werewolf = +conf, Villager = -conf
                            signed_conf = confidence if suspected == 'Werewolf' else -confidence
                            before_dict[target] = signed_conf
                    
                    after_dict = {}
                    for assessment in after_list:
                        target = assessment.get('player')
                        if target and target in state.players:
                            suspected = assessment.get('suspected_role')
                            confidence = assessment.get('confidence', 0)
                            signed_conf = confidence if suspected == 'Werewolf' else -confidence
                            after_dict[target] = signed_conf
                    
                    # Calculate absolute shifts
                    assessor_total_shift = 0
                    for target in after_dict.keys():
                        before_score = before_dict.get(target, 0)
                        after_score = after_dict[target]
                        shift = abs(after_score - before_score)
                        assessor_total_shift += shift
                    
                    if assessor_total_shift > 0:
                        assessor_shifts[assessor_name] = assessor_total_shift
                        total_shift += assessor_total_shift
                
                # Find most influenced player
                max_shift = 0
                most_influenced = ''
                if assessor_shifts:
                    most_influenced = max(assessor_shifts, key=assessor_shifts.get)
                    max_shift = assessor_shifts[most_influenced]
                
                num_influenced = len(assessor_shifts)
                
                writer.writerow([
                    speaker_name,
                    speaker_role,
                    f"{total_shift:.1f}",
                    num_influenced,
                    most_influenced
                ])
        
        print(f"Exported belief influence for round {round_idx}")
    
    # Create cross-round influence summary
    influence_summary_file = f"{directory}/influence_summary.csv"
    with open(influence_summary_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'player', 'true_role', 'total_rounds_spoke', 
            'total_belief_shift_caused', 'avg_shift_per_appearance',
            'max_shift_single_turn', 'influence_ranking'
        ])
        
        # Aggregate influence across all rounds
        player_influence = {}
        
        for round_idx, round_state in enumerate(state.rounds):
            if not round_state.role_assessments_during_debate:
                continue
                
            for turn_idx in range(len(round_state.role_assessments_during_debate)):
                if turn_idx >= len(round_state.debate):
                    continue
                    
                speaker_name = round_state.debate[turn_idx][0]
                
                if speaker_name not in player_influence:
                    player_influence[speaker_name] = {
                        'times_spoke': 0,
                        'total_shift': 0,
                        'max_shift': 0,
                        'shifts': []
                    }
                
                # Calculate shift for this turn (same logic as above)
                before_assessments = {}
                if turn_idx == 0:
                    assessments_data = scorecard_data['role_assessments']
                    for player_name in all_player_names:
                        if player_name not in round_state.players:
                            continue
                        player_data = assessments_data.get(player_name, {})
                        round_data = player_data.get('by_round', [])[round_idx] if round_idx < len(player_data.get('by_round', [])) else None
                        if round_data and round_data.get('post_night_assessment'):
                            before_assessments[player_name] = round_data['post_night_assessment'].get('assessments', [])
                else:
                    before_assessments = round_state.role_assessments_during_debate[turn_idx - 1]
                
                after_assessments = round_state.role_assessments_during_debate[turn_idx]
                
                total_shift = 0
                for assessor_name, after_data in after_assessments.items():
                    if assessor_name == speaker_name:
                        continue
                    
                    if turn_idx == 0:
                        before_list = before_assessments.get(assessor_name, [])
                    else:
                        before_data = before_assessments.get(assessor_name, {})
                        before_list = before_data.get('assessments', [])
                    
                    after_list = after_data.get('assessments', [])
                    
                    before_dict = {}
                    for assessment in before_list:
                        target = assessment.get('player')
                        if target and target in state.players:
                            suspected = assessment.get('suspected_role')
                            confidence = assessment.get('confidence', 0)
                            signed_conf = confidence if suspected == 'Werewolf' else -confidence
                            before_dict[target] = signed_conf
                    
                    after_dict = {}
                    for assessment in after_list:
                        target = assessment.get('player')
                        if target and target in state.players:
                            suspected = assessment.get('suspected_role')
                            confidence = assessment.get('confidence', 0)
                            signed_conf = confidence if suspected == 'Werewolf' else -confidence
                            after_dict[target] = signed_conf
                    
                    assessor_shift = sum(abs(after_dict.get(t, 0) - before_dict.get(t, 0)) for t in after_dict.keys())
                    total_shift += assessor_shift
                
                player_influence[speaker_name]['times_spoke'] += 1
                player_influence[speaker_name]['total_shift'] += total_shift
                player_influence[speaker_name]['shifts'].append(total_shift)
                player_influence[speaker_name]['max_shift'] = max(player_influence[speaker_name]['max_shift'], total_shift)
        
        # Sort by total influence and write
        sorted_players = sorted(player_influence.items(), key=lambda x: x[1]['total_shift'], reverse=True)
        
        for rank, (player_name, data) in enumerate(sorted_players, 1):
            player_role = state.players[player_name].role if player_name in state.players else 'Unknown'
            times_spoke = data['times_spoke']
            total_shift = data['total_shift']
            avg_shift = total_shift / times_spoke if times_spoke > 0 else 0
            max_shift = data['max_shift']
            
            writer.writerow([
                player_name,
                player_role,
                times_spoke,
                f"{total_shift:.1f}",
                f"{avg_shift:.1f}",
                f"{max_shift:.1f}",
                rank
            ])
    
    print(f"Exported influence summary to {influence_summary_file}")
    
    # Create a game summary CSV
    summary_file = f"{directory}/game_summary.csv"
    with open(summary_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'player', 'true_role', 'survived', 'round_eliminated', 'round_exiled',
            'total_votes_cast', 'total_debates_participated'
        ])
        
        for player_name in all_player_names:
            player = state.players[player_name]
            scorecard = scorecard_data['player_scorecard'].get(player_name, {})
            
            # Check if survived
            survived = player_name in state.rounds[-1].players if state.rounds else False
            
            # Find elimination/exile round
            round_eliminated = None
            round_exiled = None
            for r_idx, round_state in enumerate(state.rounds):
                if round_state.eliminated == player_name:
                    round_eliminated = r_idx
                if round_state.exiled == player_name:
                    round_exiled = r_idx
            
            # Count stats
            total_votes = len(scorecard.get('voted_for', []))
            total_debates = len(scorecard.get('debate_contributions', []))
            
            writer.writerow([
                player_name,
                player.role,
                'Yes' if survived else 'No',
                round_eliminated if round_eliminated is not None else '',
                round_exiled if round_exiled is not None else '',
                total_votes,
                total_debates
            ])
    
    print(f"Exported game summary to {summary_file}")


# Saves analysis and suspicion scorecard to a file
def save_analysis(state, logs, directory: str):
    scorecard_data = generate_suspicion_scorecard(state, logs)
    
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
        'suspicion_scorecard': scorecard_data['player_scorecard'],
        'role_assessments': scorecard_data['role_assessments'],
        'analysis_notes': {
            'description': 'This file contains reasoning analysis for each player',
            'suspicion_scorecard_explanation': {
                'voted_for': 'History of who they voted for and why',
                'debate_contributions': 'What they said in debates with reasoning',
                'reasoning_history': 'Round-by-round breakdown of all their reasoning'
            },
            'role_assessments_explanation': {
                'description': 'Internal scorecard tracking what role each player thinks every other player has',
                'post_night_assessment': 'Role beliefs after night actions are revealed, before debate',
                'debate_turn_assessments': 'Role beliefs after each player speaks during debate',
                'confidence': 'Each assessment includes confidence level (1-100): 1=not confident, 100=absolutely certain'
            }
        }
    }
    
    analysis_file = f"{directory}/analysis_metrics.json"
    with open(analysis_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Analysis metrics saved to: {analysis_file}")
    
    # Export per-round CSVs
    export_round_csvs(state, logs, scorecard_data, directory)
    
    return analysis_file
