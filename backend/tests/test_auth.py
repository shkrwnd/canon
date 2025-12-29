import pytest
from fastapi import status


def test_register_user(client):
    """Test user registration"""
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_register_duplicate_email(client):
    """Test registration with duplicate email"""
    # Register first user
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    
    # Try to register again with same email
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_login(client):
    """Test user login"""
    # Register first
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    
    # Login
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()


def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED



