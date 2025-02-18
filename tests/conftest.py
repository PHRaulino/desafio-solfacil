import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database import Base, crud, get_db, schemas
from src.main import app

db_file = "./tests/database/test.db"
os.remove(db_file) if os.path.exists(db_file) else None
SQLALCHEMY_DATABASE_URL = "sqlite:///{}".format(db_file)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


@pytest.fixture(scope="module")
def db() -> Session:
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="function")
def client(db) -> TestClient:
    def override_get_db():
        try:
            yield db
        finally:
            db.rollback()

    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_zipcode_response(requests_mock):
    url = "https://viacep.com.br/ws/01156325/json/"
    json = {
        "cep": "01156-325",
        "logradouro": "Rua Patativa da Santa Maria",
        "complemento": "",
        "bairro": "Colônia Dona Luíza",
        "localidade": "Ponta Grossa",
        "uf": "PR",
        "ibge": "4119905",
        "gia": "",
        "ddd": "42",
        "siafi": "7777",
    }

    requests_mock.get(url, status_code=200, json=json)
    return url, json


@pytest.fixture
def mock_zipcode_response_error(requests_mock):
    url = "https://viacep.com.br/ws/01156325/json/"
    json = {"erro": True}

    requests_mock.get(url, status_code=200, json=json)
    return url, json


@pytest.fixture(scope="function")
def test_partners(db, client, mock_zipcode_response):
    partners = [
        {"cnpj": "32402779000168", "cep": "01156325"},
        {"cnpj": "16470954000106", "cep": "01156325"},
        {
            "cnpj": "69971725000123",
            "cep": "01156325",
            "email": "company@company.com",
        },
    ]

    for partner in partners:
        crud.create_partner(db, schemas.PartnerJsonSchema.parse_obj(partner))
