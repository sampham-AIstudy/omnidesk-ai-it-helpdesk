import pytest


@pytest.mark.asyncio
async def test_password_reset_request_is_a_real_identity_workflow(client, auth_employee):
    response = await client.post(
        "/api/v1/service-requests",
        json={
            "service_name": "Đặt lại mật khẩu",
            "category": "accounts",
            "form_data": {"requested_from": "employee_profile"},
        },
        headers={"Authorization": f"Bearer {auth_employee}"},
    )

    assert response.status_code == 201
    assert response.json()["fulfillment_group"] == "Identity & Access"
    assert response.json()["status"] == "submitted"
