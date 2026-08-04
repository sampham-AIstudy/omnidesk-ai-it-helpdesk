from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_admin_can_create_update_and_delete_kb_entry(client, auth_admin):
    if not auth_admin:
        pytest.skip("No auth token")

    headers = {"Authorization": f"Bearer {auth_admin}"}

    with patch("src.api.admin.index_document") as mock_index:
        create_resp = await client.post(
            "/api/v1/admin/kb",
            json={
                "title": "Healthcare ICU printer reset",
                "content": "Steps for resetting secured ICU label printers.",
                "solution": "Restart spooler and re-pair the printer.",
                "category": "hardware",
                "tags": "printer,icu",
                "company_unit": "healthcare",
                "department": "ICU",
                "applicable_to_all": False,
            },
            headers=headers,
        )

    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["department"] == "ICU"
    mock_index.assert_called_once()

    with patch("src.api.admin.index_document") as mock_index:
        update_resp = await client.patch(
            f"/api/v1/admin/kb/{created['id']}",
            json={"solution": "Restart spooler, clear queue, then re-pair the printer."},
            headers=headers,
        )

    assert update_resp.status_code == 200
    assert "clear queue" in update_resp.json()["solution"]
    mock_index.assert_called_once()

    with patch("src.api.admin.delete_document") as mock_delete:
        delete_resp = await client.delete(
            f"/api/v1/admin/kb/{created['id']}",
            headers=headers,
        )

    assert delete_resp.status_code == 204
    mock_delete.assert_called_once()


@pytest.mark.asyncio
async def test_employee_cannot_create_kb_entry(client, auth_employee):
    if not auth_employee:
        pytest.skip("No auth token")

    resp = await client.post(
        "/api/v1/admin/kb",
        json={
            "title": "Unauthorized KB",
            "content": "Employee should not be able to create this.",
            "category": "software",
        },
        headers={"Authorization": f"Bearer {auth_employee}"},
    )

    assert resp.status_code == 403
