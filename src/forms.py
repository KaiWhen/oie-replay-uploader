import pickle
import requests
from apiclient import discovery
from httplib2 import Http
from oauth2client import client, file, tools
from dateutil import parser
from datetime import datetime
from mongo import status_col, scores_col
from osuapi import osuapi


SCOPES = "https://www.googleapis.com/auth/forms.responses.readonly"
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"

BASE_URL = "https://osu.ppy.sh/api/v2"


def authenticate():
    store = file.Storage('tokens/form_token.json')
    creds = store.get()
    if creds is None or creds.invalid:
        flow = client.flow_from_clientsecrets('tokens/form_secrets.json', SCOPES)
        # args = tools.argparser.parse_args()
        # args.noauth_local_webserver = True
        creds = tools.run_flow(flow, store)
    service = discovery.build('forms', 'v1', http=creds.authorize(
        Http()), discoveryServiceUrl=DISCOVERY_DOC, static_discovery=False)
    return service

service = authenticate()

def get_form_resp():
    update_status = status_col.find_one({'country': 'IE'})
    form_id = '1quic99kn_XTBrMaZA8un_j3Xr5Xk98wY2-bYwteQx5s'
    result = service.forms().responses().list(formId=form_id).execute()
    score_ids = []
    if 'responses' not in result:
        return score_ids
    for resp in result['responses']:
        resp_time_obj = parser.isoparse(resp['lastSubmittedTime'])
        resp_timestamp = resp_time_obj.timestamp()
        if resp_timestamp - update_status['form_updated'] >= 0:
            score_id = resp['answers']['7f0c0670']['textAnswers']['answers'][0]['value']
            score_obj = None
            score_obj = get_score(score_id)
            if score_obj is None:
                continue
            score = scores_col.find_one({'score_id': int(score_obj['id'])})
            if score or not score_obj['replay']:
                continue
            score_ids.append(score_obj['id'])

    now = datetime.now()
    timestamp_now = datetime.timestamp(now)
    status_col.update_one({
    'country': 'IE'
    },{
        '$set': {
            'form_updated': timestamp_now
        }
    }, upsert=False)

    return score_ids


def get_score(score_id):
    with open('tokens/osutoken.pickle', 'rb') as handle:
        osu_token = pickle.load(handle)

    headers = {'Authorization': f'Bearer {osu_token["access_token"]}'}

    try:
        resp = requests.get(f"{BASE_URL}/scores/osu/{score_id}", headers=headers)
    except Exception as e:
        print(f"Error: {e}")
        return None

    if not resp.ok:
        return None
    
    score = resp.json()
    # score_obj = {
    #     'id': score['id'],
    #     'replay': score['replay'],
    # }
    
    return score


# get_score(4666889190)

# def test():
#     SCOPES = "https://www.googleapis.com/auth/forms.responses.readonly"
#     DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"

#     store = file.Storage('tokens/form_token.json')
#     creds = store.get()
#     if not creds or creds.invalid:
#         flow = client.flow_from_clientsecrets('tokens/form_secrets.json', SCOPES)
#         creds = tools.run_flow(flow, store)
#     service = discovery.build('forms', 'v1', http=creds.authorize(
#         Http()), discoveryServiceUrl=DISCOVERY_DOC, static_discovery=False)

#     update_status = status_col.find_one({'country': 'IE'})
#     form_id = '10uyLvQ3Lm_NXJN7M92Dyg3FfY3BYpo98ojHBL7OueJc'
#     result = service.forms().responses().list(formId=form_id).execute()
#     score_ids = []
#     if 'responses' not in result:
#         return score_ids
#     for resp in result['responses']:
#         print(resp)

# test()


# https://drive.google.com/u/0/uc?id=1oKNU8oY2eLjORF_qa_0JPQm8W1aoTeTd&export=download

# # print(isinstance("3948943", int))
# score_obj = osuapi.score(mode="osu", score_id=457136312)

# # scores_top10 = osuapi.user_scores(user_id=10276624, type="best", limit=10, mode="osu")
# print(score_obj)

# get_form_resp()

