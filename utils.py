import glob
import mimetypes
import os.path
import urllib.parse
from typing import List

import requests
from openpyxl.cell import Cell


def get_account_id(token, url) -> str:
    urn = 'accounts'
    uri = urllib.parse.urljoin(url, urn)
    headers = {
        'Authorization': f'Bearer {token}'
    }
    r = requests.get(uri, headers=headers)
    assert r.ok, 'Something went wrong with getting account id'
    return str(r.json()['items'][0]['id'])


def get_all_vacancies(token, url, account_id: str):
    urn = f"/account/{account_id}/vacancies"
    uri = urllib.parse.urljoin(url, urn)
    headers = {
        'Authorization': f'Bearer {token}'
    }
    r = requests.get(uri, headers=headers)
    assert r.ok, 'Something went wrong with getting all vacancies'
    return r.json()['items']


def get_all_statuses(token, url, account_id: str):
    urn = f"/account/{account_id}/vacancy/statuses"
    uri = urllib.parse.urljoin(url, urn)
    headers = {
        'Authorization': f'Bearer {token}'
    }
    r = requests.get(uri, headers=headers)
    assert r.ok, 'Something went wrong with getting all statuses'
    return r.json()['items']


def upload_cv_of_candidate(token, url, account_id, file_path):
    urn = f"/account/{account_id}/upload"
    uri = urllib.parse.urljoin(url, urn)
    headers = {
        'Authorization': f'Bearer {token}',
        'X-File-Parse': 'true'
    }
    file_name = os.path.split(file_path)[-1]
    mime_type = mimetypes.guess_type(file_name)[0]
    files = [
        ('file', (file_name, open(file_path, 'rb'), mime_type))
    ]
    r = requests.post(uri, headers=headers, files=files)
    assert r.ok, 'Something went wrong with uploading candidate resume'
    return r.json()


def insert_candidate(token: str, url: str, account_id: str, row: List[Cell]):
    pattern_glob = f"./{row[0].value.strip()}/{row[1].value.strip()}*"
    candidate_cv_file_path = glob.glob(pattern_glob)
    assert len(candidate_cv_file_path) == 1, 'Something went wrong with getting path of cv file'
    candidate_resume_file_path = candidate_cv_file_path[0]
    upload_cv_response = upload_cv_of_candidate(token, url, account_id, candidate_resume_file_path)
    headers = {
        'Authorization': f'Bearer {token}'
    }
    urn = 'applicants'
    uri = urllib.parse.urljoin(url, f"/account/{account_id}/{urn}")
    last_name, first_name, *middle_name = row[1].value.split()
    middle_name = middle_name[0] if middle_name else ''
    splitted_money = str(row[2].value).split()  # Normalizing money
    if splitted_money[-1].isalpha():
        *splitted_money, currency = splitted_money
    else:
        currency = 'рублей'
    money = f"{int(float(''.join(splitted_money)))} {currency}"
    position = row[0].value.strip()
    phone = None
    email = None
    birthday_day = None
    birthday_month = None
    birthday_year = None
    photo_id = None

    if 'phones' in upload_cv_response['fields'] \
            and upload_cv_response['fields']['phones']:
        phone = upload_cv_response['fields']['phones'][0]

    if 'email' in upload_cv_response['fields']:
        email = upload_cv_response['fields']['email']

    if 'birthdate' in upload_cv_response['fields'] \
            and upload_cv_response['fields']['birthdate']:

        if 'day' in upload_cv_response['fields']['birthdate']:
            birthday_day = upload_cv_response['fields']['birthdate']['day']

        if 'month' in upload_cv_response['fields']['birthdate']:
            birthday_month = upload_cv_response['fields']['birthdate']['month']

        if 'year' in upload_cv_response['fields']['birthdate']:
            birthday_year = upload_cv_response['fields']['birthdate']['year']

    if 'photo' in upload_cv_response \
            and upload_cv_response['photo']:
        photo_id = upload_cv_response['photo']['id']

    data = {
        'last_name': last_name.capitalize(),
        'first_name': first_name.capitalize(),
        'middle_name': middle_name.capitalize(),
        "phone": phone,
        "email": email,
        "position": position,
        "company": None,
        "money": money,
        "birthday_day": birthday_day,
        "birthday_month": birthday_month,
        "birthday_year": birthday_year,
        "photo": photo_id,
        "externals": [
            {
                "data": {
                    "body": upload_cv_response['text']
                },
                "files": [
                    {
                        "id": upload_cv_response['id']
                    }
                ],
                'auth_type': "NATIVE"  # Текстовый формат
            }
        ]
    }
    r = requests.post(
        uri,
        json=data,
        headers=headers
    )
    assert r.ok, 'Something went wrong with creating candidate'
    return r.json()


def get_vacancy(vacancies: list[dict], vacancy_name: str) -> dict:
    vacancy = list(filter(lambda x: x['position'].lower() == vacancy_name.lower(), vacancies))
    assert len(vacancy) == 1, 'Something went wrong with getting vacancy'
    return vacancy[0]


def get_status(statuses: list[dict], status_name: str) -> dict:
    status = list(filter(lambda x: x['name'].lower() == status_name.lower(), statuses))
    assert len(status) == 1, 'Something went wrong with getting status'
    return status[0]

def get_fill_quota(token, url, account_id, vacancy_id) -> int:
    urn = f"/account/{account_id}/vacancy/{vacancy_id}/quotas"
    uri = urllib.parse.urljoin(url, urn)
    headers = {
        'Authorization': f'Bearer {token}'
    }
    r = requests.get(uri, headers=headers)
    assert r.ok, 'Something went wrong woth getting fill quotas'
    fill_quotas = r.json()['1']['items']
    assert len(fill_quotas) == 1, 'Length of fill_quotas is greater than 1'
    return fill_quotas[0]


def connect_candidate_to_vacancy(token, url, account_id, row: List[Cell],
                                 vacancy_id, status_id, candidate_cv):
    urn = f"/account/{account_id}/applicants/{candidate_cv['id']}/vacancy"
    uri = urllib.parse.urljoin(url, urn)
    headers = {
        'Authorization': f'Bearer {token}'
    }
    data = {
        "vacancy": vacancy_id,
        "status": status_id,
        "comment": row[3].value.strip(),
        "files": [
            {"id": external['id']} for external in candidate_cv['external']
        ]
    }
    """
    Во время выполнения тестового задания нигде в документации не нашел способ получения id rejection_reason
    """
    r = requests.post(
        uri,
        json=data,
        headers=headers
    )
    print(r.json())
    assert r.ok, 'Something went wrong with connection candidate to vacancy'

