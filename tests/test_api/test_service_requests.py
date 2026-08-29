"""Service Requests use their own API and never create Incident tickets."""
import pytest


@pytest.mark.asyncio
async def test_create_and_read_service_request(client, auth_employee):
    if not auth_employee:
        pytest.skip("No auth token")
    headers = {"Authorization": f"Bearer {auth_employee}"}
    create = await client.post(
        "/api/v1/service-requests",
        json={
            "service_name": "Xin quyền VPN",
            "category": "access",
            "form_data": {"account": "employee1@corp.example.com", "justification": "Cần truy cập môi trường dự án từ xa."},
        },
        headers=headers,
    )
    assert create.status_code == 201
    request = create.json()
    assert request["request_number"].startswith("REQ-")
    assert request["status"] == "pending_approval"
    assert request["fulfillment_group"] == "Network & Security"

    mine = await client.get("/api/v1/service-requests/mine", headers=headers)
    assert mine.status_code == 200
    assert any(item["request_number"] == request["request_number"] for item in mine.json()["items"])

    detail = await client.get(f"/api/v1/service-requests/{request['request_number']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["service_name"] == "Xin quyền VPN"


@pytest.mark.asyncio
async def test_catalog_is_authoritative_for_request_routing(client, auth_employee):
    headers = {"Authorization": f"Bearer {auth_employee}"}
    catalog = await client.get("/api/v1/service-requests/catalog", headers=headers)
    assert catalog.status_code == 200
    vpn = next(item for item in catalog.json()["items"] if item["service_name"] == "Xin quyền VPN")
    assert vpn == {
        "service_name": "Xin quyền VPN",
        "category": "access",
        "fulfillment_group": "Network & Security",
        "approval_roles": ["admin"],
        "risk_level": "medium",
        "sla_hours": 4,
    }

    created = await client.post(
        "/api/v1/service-requests",
        json={"service_name": "Xin quyền VPN", "category": "accounts", "form_data": {}},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["category"] == "access"
