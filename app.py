from flask import Flask, render_template, request
import requests

app = Flask(__name__)

# Url da API da MLB
API_URL = "https://statsapi.mlb.com/api/v1/"


# Função para extrair dados da API a partir de um endpoint e parâmetros
def fetch_data(endpoint, params):
    url = API_URL + endpoint
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None


# Função que consegue highlights da maioria dos jogos desde 24/09/2018
def get_condensed_game(data):
    if isinstance(data, dict):
        title = data.get("title", "")
        if ((title.startswith("Condensed Game:") or title.startswith("CG:") or title.startswith("Recap:")) and
                "duration" in data):
            for playback in data.get("playbacks", []):
                if playback.get("name") == "mp4Avc":
                    return playback.get("url")
                if playback.get("name") == "FLASH_2500K_1280X720":
                    return playback.get("url")
        for key, value in data.items():
            result = get_condensed_game(value)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = get_condensed_game(item)
            if result:
                return result
    return None


# Função que extrai detalhes de um jogo dado o seu id
def get_game_details(game_id):
    params = {}
    data = fetch_data(f"game/{game_id}/content", params)

    if not data:
        return None

    highlight_url = get_condensed_game(data)

    if highlight_url:
        return highlight_url
    else:
        return None


# Função para buscar os detalhes do jogador com base no ID
def get_player_details(player_id):
    params = {}
    data = fetch_data(f"people/{player_id}", params)

    if data:
        player_data = data['people'][0]

        player_details = {
            'full_name': player_data['fullName'],
            'nickname': player_data.get('nickName', 'N/A'),
            'position': player_data['primaryPosition']['name'] if player_data.get('primaryPosition') else 'N/A',
            'birthplace': f"{player_data.get('birthCity', 'N/A')}, {player_data.get('birthCountry', 'N/A')}",
            'birthdate': player_data.get('birthDate', 'N/A'),
            'age': player_data.get('currentAge', 'N/A'),
            'height': player_data.get('height', 'N/A'),
            'weight': player_data.get('weight', 'N/A'),
            'mlb_debut': player_data.get('mlbDebutDate', 'N/A'),
            'bats': player_data.get('batSide', {}).get('description', 'N/A'),
            'throws': player_data.get('pitchHand', {}).get('description', 'N/A'),
            'photo_url': f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{player_data['id']}/headshot/67/current"
        }

        return player_details
    return None


# Função para buscar os detalhes do time com base no ID
def get_team_details(team_id):
    params = {
    }
    return fetch_data(f"teams/{team_id}", params)


def get_team_roster(team_id):
    params = {
    }
    return fetch_data(f"teams/{team_id}/roster", params)


# Função que extrai os líderes de uma determinada categoria estatística em um ano
def get_leaders(year, leagueId, leaderCategories, statGroup):
    params = {
        'leaderCategories': [{leaderCategories}],
        'season': year,
        'limit': 3,
        'leagueId': leagueId,
        'statGroup': [{statGroup}]
    }

    return fetch_data("stats/leaders", params)


# Função que extrai as colocações dos times em um ano
def get_standings(year):
    params = {
        'season': year,
        'leagueId': [103, 104]  # AL e NL, respectivamente
    }

    data = fetch_data("standings", params)

    if data:
        american_league_standings = []
        national_league_standings = []

        for record in data['records']:
            league_id = record['league']['id']

            if league_id == 103:  # American League
                american_league_standings.extend(record['teamRecords'])
            elif league_id == 104:  # National League
                national_league_standings.extend(record['teamRecords'])

        # Ordena os times por número de vitórias
        american_league_standings = sorted(american_league_standings, key=lambda x: x['wins'], reverse=True)
        national_league_standings = sorted(national_league_standings, key=lambda x: x['wins'], reverse=True)

        return american_league_standings, national_league_standings
    return None, None


# Função que extrai o todos os jogos de temporada regular ou playoffs de uma temporada
def get_schedule(year):
    params = {
        'sportId': 1,
        'season': year
    }

    data = fetch_data("schedule", params)

    if data:
        games = []
        for date_info in data['dates']:
            date = date_info['date']
            for game in date_info['games']:
                if game['gameType'] in ['R', 'F', 'D', 'L', 'W'] and game['teams']['home'].get('score') is not None:
                    home_team = game['teams']['home']['team']['name']
                    home_team_id = game['teams']['home']['team']['id']
                    away_team = game['teams']['away']['team']['name']
                    away_team_id = game['teams']['away']['team']['id']
                    home_score = game['teams']['home'].get('score')
                    away_score = game['teams']['away'].get('score')
                    score = f"{home_score} - {away_score}"
                    game_id = game['gamePk']

                    games.append({
                        'date': date,
                        'home_team': home_team,
                        'home_team_id': home_team_id,
                        'away_team': away_team,
                        'away_team_id': away_team_id,
                        'score': score,
                        'game_id': game_id
                    })
        return games
    return None


# Rota para idnex
@app.route('/')
def index():
    return render_template('index.html')


# Rota para gamedetails
@app.route('/gamedetails/<int:game_id>')
def gamedetails(game_id):
    highlight_url = get_game_details(game_id)

    if highlight_url:
        # Aqui você pode passar outras informações do jogo junto com a URL do vídeo
        game_data = {
            'game_id': game_id,
            'highlight_url': highlight_url
        }
        return render_template('gamedetails.html', game_data=game_data)
    else:
        return "Não há conteúdo disponível para esse jogo."


# Rota para player
@app.route('/player/<int:player_id>', methods=['GET'])
def player(player_id):
    player_data = get_player_details(player_id)

    if player_data:
        return render_template('player.html', player_data=player_data)
    else:
        return "Error fetching data from MLB API for player"


# Rota para team
@app.route('/teams/<int:team_id>', methods=['GET'])
def team(team_id):
    team_data = get_team_details(team_id)
    team_roster = get_team_roster(team_id)

    # Prepare os dados do time
    if not team_data or not team_data.get('teams'):
        return "Error fetching data from MLB API for team"

    team_info = {
        'id': team_data['teams'][0]['id'],
        'name': team_data['teams'][0]['name'],
        'stadium': team_data['teams'][0]['venue']['name'],
        'division': team_data['teams'][0]['division']['name'],
        'logo_url': f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{team_data['teams'][0]['id']}.svg",
    }

    # Prepare a lista de jogadores
    roster = []
    if team_roster and team_roster.get('roster'):
        roster = [
            {
                'name': player['person']['fullName'],
                'id': player['person']['id'],
                'jerseyNumber': player.get('jerseyNumber', 'N/A'),
                'position': player['position']['name'],
            }
            for player in team_roster['roster']
        ]

    return render_template('team.html', team_info=team_info, roster=roster)


# Rota para leaders
@app.route('/leaders', methods=['GET'])
def leaders():
    categories = {
        'earnedRunAverage': {'display': 'Earned Run Average', 'statGroup': 'pitching'},
        'wins': {'display': 'Wins', 'statGroup': 'pitching'},
        'battingAverage': {'display': 'Batting Average', 'statGroup': 'hitting'},
        'stolenBases': {'display': 'Stolen Bases', 'statGroup': 'hitting'},
        'onBasePercentage': {'display': 'On Base Percentage', 'statGroup': 'hitting'},
        'runs': {'display': 'Runs', 'statGroup': 'hitting'}
    }

    year = request.args.get('year', type=int, default=2024)
    leaderCategories = request.args.get('leaderCategories', type=str, default='battingAverage')  # Default category if not provided
    statGroup = categories.get(leaderCategories, {}).get('statGroup', 'hitting')

    # Get data for both leagues
    american_league = get_leaders(year, 103, leaderCategories, statGroup)
    national_league = get_leaders(year, 104, leaderCategories, statGroup)

    # Prepare data for rendering
    leaders_data = {'american_league': [], 'national_league': []}

    if american_league:
        for category in american_league['leagueLeaders']:
            for leader in category['leaders']:
                leaders_data['american_league'].append({
                    'rank': leader['rank'],
                    'name': leader['person']['fullName'],
                    'team': leader['team']['name'],
                    'value': leader['value'],
                    'player_id': leader['person']['id'],
                    'team_id': leader['team']['id']
                })

    if national_league:
        for category in national_league['leagueLeaders']:
            for leader in category['leaders']:
                leaders_data['national_league'].append({
                    'rank': leader['rank'],
                    'name': leader['person']['fullName'],
                    'team': leader['team']['name'],
                    'value': leader['value'],
                    'player_id': leader['person']['id'],
                    'team_id': leader['team']['id']
                })

    # Pass the preprocessed data to the template
    return render_template('leaders.html',
                           leaders_data=leaders_data,
                           year=year,
                           leaderCategories=leaderCategories,
                           categories=categories)


# Rota para standings
@app.route('/standings', methods=['GET'])
def standings():
    year = request.args.get('year', type=int)
    if not year:
        year = 2024  # Default to 2024 if no year is provided
    american_league, national_league = get_standings(year)

    if american_league and national_league:
        return render_template('standings.html',
                               american_league=american_league,
                               national_league=national_league,
                               year=year)
    else:
        return "Error fetching data from MLB API for standings"


# Rota para schedule
@app.route('/schedule', methods=['GET'])
def schedule():
    year = request.args.get('year', type=int)
    games = get_schedule(year)

    if games:
        return render_template('schedule.html', games=games, year=year)
    else:
        return "Error fetching data from MLB API for schedule"


if __name__ == '__main__':
    app.run(debug=True)
