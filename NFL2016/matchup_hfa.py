import os
import sys
import pandas as pd
import numpy as np
from numpy.random import poisson, uniform
from numpy import mean
import time
import math

po = True

teamsheetpath = sys.path[0] + '/teamcsvs/'

compstat = {'TDF': 'TDA', 'TDA': 'TDF', #Dictionary to use to compare team stats with opponent stats
            'FGF': 'FGA', 'FGA': 'FGF',
            'SFF': 'SFA', 'SFA': 'SFF',
            'PAT1%F': 'PAT1%A', 'PAT1%A': 'PAT1%F',
            'PAT2%F': 'PAT2%A', 'PAT2%A': 'PAT2%F'}

def logit(p):
    return np.log(p) - np.log(1-p)

def sigmoid(x):
    return 1/(1+np.exp(-x))

def logitadd(addends):
    logit_addends = logit(addends)
    return sigmoid(logit_addends.sum())

def probadd(probs):
    addends = (probs+1)/2
    sum = logitadd(addends)
    return 2*sum - 1

def round_percentage(percentage):
    '''
    Removes `.0` from a string containing a percentage

    Parameters
    ----------
    percentage (str):
        Percentage to round

    Returns
    -------
    percentage (str):
        Rounded percentage
    '''
    return percentage.replace('.0', '')

def get_opponent_stats(opponent):
    '''
    Calculates the statistics of each teams oppopnent

    Parameters
    ----------
    opponent (str):
        Week's opponent
    hfa (int):
        1 if team is at home, 0 if neutral, -1 if on the road

    Returns
    -------
    opponent_stats (dict):
        Dictionary of statistics
    '''
    opponent_stats = {}
    global teamsheetpath
    opp_stats = pd.DataFrame.from_csv(teamsheetpath + opponent + '.csv')

    #Compute easy to calculate stats
    for stat in opp_stats.columns:
        if stat in ['TDF', 'FGF', 'SFF', 'TDA', 'FGA', 'SFA']:
            opponent_stats[stat] = opp_stats[stat].mean()

    #Calculate percentages. If unable, insert assumed values
    try:
        opponent_stats['PAT1%F'] = float(opp_stats['PAT1FS'].sum()) / opp_stats['PAT1FA'].sum()
    except ZeroDivisionError:
        opponent_stats['PAT1%F'] = .99
    try:
        opponent_stats['PAT2%F'] = float(opp_stats['PAT2FS'].sum()) / opp_stats['PAT2FA'].sum()
    except ZeroDivisionError:
        opponent_stats['PAT2%F'] = .5
    try:
        opponent_stats['PAT1%A'] = float(opp_stats['PAT1AS'].sum()) / opp_stats['PAT1AA'].sum()
    except ZeroDivisionError:
        opponent_stats['PAT1%A'] = .99
    try:
        opponent_stats['PAT2%A'] = float(opp_stats['PAT2AS'].sum()) / opp_stats['PAT2AA'].sum()
    except ZeroDivisionError:
        opponent_stats['PAT2%A'] = .5
    return opponent_stats

def get_residual_performance(team):
    '''
    Compares teams weekly performances to their opponents averages and gets averages of residuals

    Parameters
    ----------
    team (str):
        Team to get residual stats of

    Returns
    -------
    residual_stats (dict):
        Dictionary of team's residual stats
    '''
    global teamsheetpath
    score_df = pd.DataFrame.from_csv(teamsheetpath + team + '.csv')
    residual_stats = {}
    
    #Initialize percentages with null values
    score_df['PAT1%F'] = np.nan
    score_df['PAT2%F'] = np.nan
    score_df['PAT1%A'] = np.nan
    score_df['PAT2%A'] = np.nan

    #For each week, add in percentages. If there is no denominator, assume values. Then add fields containing opponent averages
    for week in score_df.index:
        #Make a function for this. It's a bit tedious...
        try:
            score_df['PAT1%F'][week] = float(score_df['PAT1FS'][week]) / score_df['PAT1FA'][week]
        except ZeroDivisionError:
            score_df['PAT1%F'][week] = 0.99
        try:
            score_df['PAT2%F'][week] = float(score_df['PAT2FS'][week]) / score_df['PAT2FA'][week]
        except ZeroDivisionError:
            score_df['PAT2%F'][week] = 0.5
        try:
            score_df['PAT1%A'][week] = float(score_df['PAT1AS'][week]) / score_df['PAT1AA'][week]
        except ZeroDivisionError:
            score_df['PAT1%A'][week] = 0.99
        try:
            score_df['PAT2%A'][week] = float(score_df['PAT2AS'][week]) / score_df['PAT2AA'][week]
        except ZeroDivisionError:
            score_df['PAT2%A'][week] = 0.5

        opponent_stats = get_opponent_stats(score_df['OPP'][week])
        for stat in opponent_stats:
            if week == score_df.index[0]:
                score_df['OPP_' + stat] = np.nan
            score_df['OPP_' + stat][week] = opponent_stats[stat]
            
            
    #Compute difference between team's statistics and their opponents averages, and add venue factors        
    for stat in opponent_stats:
        score_df['R_' + stat] = score_df[stat] - score_df['OPP_' + compstat[stat]]
        if stat in ['TDF', 'FGF', 'SFF', 'TDA', 'FGA', 'SFA']:
            residual_stats[stat] = score_df['R_' + stat].mean()
        elif stat == 'PAT1%F':
            residual_stats[stat] = (score_df['R_PAT1%F'].multiply(score_df['PAT1FA'])).sum() / score_df['PAT1FA'].sum()
        elif stat == 'PAT2%F':
            try:
                residual_stats[stat] = (score_df['R_PAT2%F'].multiply(score_df['PAT2FA'])).sum() / score_df['PAT2FA'].sum()
            except ZeroDivisionError:
                residual_stats[stat] = 0.0
        elif stat == 'PAT1%A':
            residual_stats[stat] = (score_df['R_PAT1%A'].multiply(score_df['PAT1AA'])).sum() / score_df['PAT1AA'].sum()
        elif stat == 'PAT2%A':
            try:
                residual_stats[stat] = (score_df['R_PAT2%A'].multiply(score_df['PAT2AA'])).sum() / score_df['PAT2AA'].sum()
            except ZeroDivisionError:
                residual_stats[stat] = 0.0
        try:
            residual_stats['GOFOR2'] = float(score_df['PAT2FA'].sum()) / score_df['TDF'].sum()
        except ZeroDivisionError:
            residual_stats['GOFOR2'] = .1
    
    return residual_stats

def get_venue_adjustments(team_df, venue):
    '''

    '''
    assert venue in [-1, 0, 1]

    if not venue:
        venue_adjustments = {'TDF': 0, 'TDA': 0,
                             'FGF': 0, 'FGA': 0,
                             'SF': 0, 'SA': 0,
                             'PAT1%F': 0, 'PAT1%A': 0,
                             'PAT2%F': 0, 'PAT2%A': 0}
        return venue_adjustments

    venue_df = team_df[team_df[venue] == venue]
    if len(venue_df.index == 0):
        venue_adjustments = {'TDF': 0, 'TDA': 0,
                             'FGF': 0, 'FGA': 0,
                             'SF': 0, 'SA': 0,
                             'PAT1%F': 0, 'PAT1%A': 0,
                             'PAT2%F': 0, 'PAT2%A': 0}
    
    else:
        venue_adjustments = {}
        for stat in venue_df:
            if stat in ['TDF', 'TDA', 'FGF', 'FGA', 'SF', 'SA']:
                venue_adjustments[stat] = venue_df[stat].mean() - team_df[stat].mean()
            try:
                venue_adjustments['PAT1%F'] = venue_df['PAT1FS']/venue_df['PAT1FA'] - team_df['PAT1FS']/team_df['PAT1FA']
            except ZeroDivisionError:
                venue_adjustments['PAT1%F'] = 0
            try:
                venue_adjustments['PAT1%A'] = venue_df['PAT1AS']/venue_df['PAT1AA'] - team_df['PAT1AS']/team_df['PAT1AA']
            except ZeroDivisionError:
                venue_adjustments['PAT1%A'] = 0
            try:
                venue_adjustments['PAT2%F'] = venue_df['PAT2FS']/venue_df['PAT2FA'] - team_df['PAT2FS']/team_df['PAT2FA']
            except ZeroDivisionError:
                venue_adjustments['PAT2%F'] = 0
            try:
                venue_adjustments['PAT2%A'] = venue_df['PAT2AS']/venue_df['PAT2AA'] - team_df['PAT2AS']/team_df['PAT2AA']
            except ZeroDivisionError:
                venue_adjustments['PAT2%F'] = 0

    return venue_adjustments

def get_expected_scores(team_1_stats, team_2_stats, team_1_df, team_2_df, team_1_adjustments, team_2_adjustments):
    '''
    Gets expected values for number of touchdowns, field goals, and safeties, as well as probabilities of going for and making PATs

    Parameters
    ----------
    team_1_stats (dict):
        Dictionary of team 1's residual statistics
    team_2_stats (dict):
        Dictionary of team 2's residual statistics
    team_1_df (dict):
        Team 1's weekly results
    team_2_df (dict):
        Team 2's weekly results

    Returns
    -------
    expected_scores (dict):
        Team 1's expected number of touchdowns, field goals, safeties, and PAT percentages
    '''
    expected_scores = {}
    
    expected_scores['TD'] = mean([team_1_stats['TDF'] + team_2_df['TDA'].mean(),
                                    team_2_stats['TDA'] + team_1_df['TDF'].mean()]) + team_1_adjustments['TDF'] + team_2_adjustments['TDA']
    expected_scores['FG'] = mean([team_1_stats['FGF'] + team_2_df['FGA'].mean(),
                                    team_2_stats['FGA'] + team_1_df['FGF'].mean()]) + team_1_adjustments['FGF'] + team_2_adjustments['FGA']
    expected_scores['S'] = mean([team_1_stats['SFF'] + team_2_df['SFA'].mean(),
                                    team_2_stats['SFA'] + team_1_df['SFF'].mean()]) + team_1_adjustments['SF'] + team_2_adjustments['SA']

    expected_scores['GOFOR2'] = team_1_stats['GOFOR2']
    pat1prob = mean([team_1_stats['PAT1%F'] + team_2_df['PAT1AS'].astype('float').sum() / team_2_df['PAT1AA'].sum(),
                        team_2_stats['PAT1%A'] + team_1_df['PAT1FS'].astype('float').sum() / team_1_df['PAT1FA'].sum()])
    if not math.isnan(pat1prob):
        expected_scores['PAT1PROB'] = pat1prob
    else:
        expected_scores['PAT1PROB'] = 0.99
        
    try:
        pat2prob = mean([team_1_stats['PAT2%F'] + team_2_df['PAT2AS'].astype('float').sum() / team_2_df['PAT2AA'].sum(),
                            team_2_stats['PAT2%A'] + team_1_df['PAT2FS'].astype('float').sum() / team_1_df['PAT2FA'].sum()])
    except ZeroDivisionError:
        pat2prob = np.nan
    if not math.isnan(pat2prob):
        expected_scores['PAT2PROB'] = pat2prob
    else:
        expected_scores['PAT2PROB'] = 0.5

    
    expected_scores['PAT1PROB'] = probadd(np.array([expected_scores['PAT1PROB'], team_1_adjustments['PAT1%F'], team_2_adjustments['PAT1%A']]))
    expected_scores['PAT2PROB'] = probadd(np.array([expected_scores['PAT2PROB'], team_1_adjustments['PAT2%F'], team_2_adjustments['PAT2%A']]))
    
    return expected_scores

def get_score(expected_scores):
    '''
    Obtains the score based on random simulation using the expected scores as expected values

    Parameters
    ----------
    expected scores (dict):
        Expected number of touchdowns, field goals, safeties, and PAT percentages

    Returns
    -------
    score (int):
        Score
    '''
    #Add contribution of touchdowns, field goals, and safeties
    score = 0
    if expected_scores['TD'] > 0:
        tds = poisson(expected_scores['TD'])
    else:
        tds = poisson(0.01) #Filler so it's not zero every time
    score = score + 6 * tds
    if expected_scores['FG'] > 0:
        fgs = poisson(expected_scores['FG'])
    else:
        fgs = poisson(0.01)
    score = score + 3 * fgs
    if expected_scores['S'] > 0:
        sfs = poisson(expected_scores['S'])
    else:
        sfs = poisson(0.01)
    score = score + 2 * sfs

    #Add PATs
    for td in range(tds):
        go_for_2_determinant = uniform(0, 1)
        if go_for_2_determinant <= expected_scores['GOFOR2']: #Going for 2
            successful_pat_determinant = uniform(0, 1)
            if successful_pat_determinant <= expected_scores['PAT2PROB']:
                score = score + 2
            else:
                continue

        else: #Going for 1
            successful_pat_determinant = uniform(0, 1)
            if successful_pat_determinant <= expected_scores['PAT1PROB']:
                score = score + 1
            else:
                continue
    return score

def game(team_1, team_2,
         expected_scores_1, expected_scores_2):
    '''
    Simulation of a single game between two teams

    Parameters
    ----------
    team_1 (str):
        Initials of team 1
    team_2 (str):
        Initials of team 2
    expected_scores_1 (dict):
        Team 1's expected scores
    expected_scores_2 (dict):
        Team 2's expected scores

    Returns
    -------
    Summary (dict):
        Summary of game's results
    '''
    score_1 = get_score(expected_scores_1)
    score_2 = get_score(expected_scores_2)

    if score_1 > score_2: #Give team 1 a win if their score is higher
        win_1 = 1.
        win_2 = 0.
    elif score_2 > score_1: #Give team 2 a win if their score is higher
        win_1 = 0.
        win_2 = 1.
    else: #If the scores are the same, give both teams a half win
        win_1 = 0.5
        win_2 = 0.5

    summary = {team_1: [win_1, score_1],
               team_2: [win_2, score_2]}

    return summary
            
def matchup(team_1, team_2, neutral = False):
    '''
    The main script. Simulates a matchup between two teams at least 5 million times

    Parameters
    ----------
    team_1 (str):
        The first team's initials
    team_2 (str):
        The second team's initials
    neutral (bool):
        Indicates whether or not the venue is being played in a neutral venue. If not, then the `team_1` is at home.

    Returns
    -------
    output (dict): #CreativeName
        Dictionary containing chances of winning and score distribution characteristics
    '''
    #Read in teams' performances and calculate expected scores based on them
    ts = time.time()
    team_1_season = pd.DataFrame.from_csv(teamsheetpath + team_1 + '.csv')
    team_2_season = pd.DataFrame.from_csv(teamsheetpath + team_2 + '.csv')

    if neutral:
        team_1_venue = 0
        team_2_venue = 0
    else:
        team_1_venue = 1
        team_2_venue = -1

    stats_1 = get_residual_performance(team_1)
    stats_2 = get_residual_performance(team_2)
    team_1_adjustments = get_venue_adjustments(team_1_season, team_1_venue)
    team_2_adjustments = get_venue_adjustments(team_2_season, team_2_venue)
    expected_scores_1 = get_expected_scores(stats_1, stats_2, team_1_season, team_2_season, team_1_adjustments, team_2_adjustments)
    expected_scores_2 = get_expected_scores(stats_2, stats_1, team_2_season, team_1_season, team_2_adjustments, team_1_adjustments)

    #Initialize with no wins or scores for each team
    team_1_wins = 0
    team_2_wins = 0
    team_1_draws = 0
    team_2_draws = 0
    team_1_scores = []
    team_2_scores = []

    #Iterate at least five million times, and then check to see if probabilities of win converge
    i = 0
    error = 1
    min_iter = int(5e6)
    while error > 0.000001 or i < min_iter: #Run until convergence after 5 million iterations
        summary = game(team_1, team_2,
                       expected_scores_1, expected_scores_2)

        team_1_prev_wins = team_1_wins
        team_1_wins += summary[team_1][0]
        team_2_wins += summary[team_2][0]
        team_1_draws += summary[team_1][1]
        team_2_draws += summary[team_2][1]
        team_1_scores.append(summary[team_1][2])
        team_2_scores.append(summary[team_2][2])
        team_1_prob = float(team_1_wins) / len(team_1_scores)
        team_2_prob = float(team_2_wins) / len(team_2_scores)

        #Compute convergence statistic after minimum iterations
        if i >= min_iter:
            team_1_prev_prob = float(team_1_prev_wins) / i
            error = team_1_prob - team_1_prev_prob
        i = i + 1
    if i == min_iter:
        print('Probability converged within %d iterations'%(min_iter))
    else:
        print('Probability converged after ' + str(i) + ' iterations')

    games = pd.DataFrame.from_items([(team_1, team_1_scores), (team_2, team_2_scores)])
    summaries = games.describe(percentiles = np.arange(0.05, 1, 0.05))

    #Remove decimal points from summary indices
    summaries = summaries.reset_index()
    summaries['index'] = summaries['index'].apply(round_percentage)
    summaries = summaries.set_index('index')

    output = {'ProbWin': {team_1: team_1_prob, team_2: team_2_prob}, 'Scores': summaries}

    print(team_1 + '/' + team_2 + ' score distributions computed in {0} seconds'.format(round(time.time() - ts, 1)))

    return output