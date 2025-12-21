import pytest
from fastapi import status


@pytest.fixture
def auth_token(client):
    """Get authentication token"""
    client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    return response.json()["access_token"]


def test_create_module(client, auth_token):
    """Test creating a module"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        "/api/modules",
        json={"name": "Test Module", "content": "Test content"},
        headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "Test Module"


def test_list_modules(client, auth_token):
    """Test listing modules"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a module first
    client.post(
        "/api/modules",
        json={"name": "Test Module", "content": "Test content"},
        headers=headers
    )
    
    # List modules
    response = client.get("/api/modules", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) > 0


def test_get_module(client, auth_token):
    """Test getting a specific module"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a module
    create_response = client.post(
        "/api/modules",
        json={"name": "Test Module", "content": "Test content"},
        headers=headers
    )
    module_id = create_response.json()["id"]
    
    # Get the module
    response = client.get(f"/api/modules/{module_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == module_id


def test_update_module(client, auth_token):
    """Test updating a module"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a module
    create_response = client.post(
        "/api/modules",
        json={"name": "Test Module", "content": "Test content"},
        headers=headers
    )
    module_id = create_response.json()["id"]
    
    # Update the module
    response = client.put(
        f"/api/modules/{module_id}",
        json={"name": "Updated Module", "content": "Updated content"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Updated Module"


def test_delete_module(client, auth_token):
    """Test deleting a module"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create a module
    create_response = client.post(
        "/api/modules",
        json={"name": "Test Module", "content": "Test content"},
        headers=headers
    )
    module_id = create_response.json()["id"]
    
    # Delete the module
    response = client.delete(f"/api/modules/{module_id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify it's deleted
    get_response = client.get(f"/api/modules/{module_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


