"""Unit tests for service modules."""
import json

import pytest

from app.schemas.meeting import MeetingAnalysisResult
from app.utils.permissions import RoleEnum, has_permission


class TestPermissions:
    def test_superadmin_has_all_permissions(self):
        assert has_permission(RoleEnum.SUPERADMIN, RoleEnum.CEO)
        assert has_permission(RoleEnum.SUPERADMIN, RoleEnum.LINE)

    def test_ceo_has_manager_permissions(self):
        assert has_permission(RoleEnum.CEO, RoleEnum.CEO_1)
        assert has_permission(RoleEnum.CEO, RoleEnum.LINE)

    def test_line_has_no_elevated_permissions(self):
        assert not has_permission(RoleEnum.LINE, RoleEnum.CEO)
        assert not has_permission(RoleEnum.LINE, RoleEnum.MIDDLE)

    def test_same_role_has_permission(self):
        assert has_permission(RoleEnum.CEO, RoleEnum.CEO)
        assert has_permission(RoleEnum.LINE, RoleEnum.LINE)

    def test_hierarchy_is_strict(self):
        assert not has_permission(RoleEnum.CEO_1, RoleEnum.CEO)
        assert not has_permission(RoleEnum.MIDDLE, RoleEnum.CEO_2)


class TestMeetingAnalysisResult:
    def test_valid_analysis_result(self):
        result = MeetingAnalysisResult(
            summary="Test summary",
            decisions=[{"content": "Decision 1", "responsible_name": "John"}],
            tasks=[{"title": "Task 1", "assignee_name": "Jane", "priority": "high"}],
            key_points=["Point 1", "Point 2"],
            risks=["Risk 1"],
            water_percentage=15.5,
            contradictions=[],
        )
        assert result.summary == "Test summary"
        assert len(result.decisions) == 1
        assert len(result.tasks) == 1
        assert result.water_percentage == 15.5

    def test_empty_analysis_result(self):
        result = MeetingAnalysisResult(
            summary="Empty meeting",
            decisions=[],
            tasks=[],
            key_points=[],
            risks=[],
            water_percentage=0,
        )
        assert len(result.decisions) == 0
        assert len(result.contradictions) == 0

    def test_analysis_from_json(self):
        raw = json.dumps({
            "summary": "Обсуждение Q2",
            "decisions": [{"content": "Увеличить бюджет"}],
            "tasks": [{"title": "Подготовить отчёт", "priority": "high"}],
            "key_points": ["Рост выручки"],
            "risks": ["Нехватка кадров"],
            "water_percentage": 22.0,
            "contradictions": [],
        })
        data = json.loads(raw)
        result = MeetingAnalysisResult(**data)
        assert result.summary == "Обсуждение Q2"
        assert result.water_percentage == 22.0


class TestSchemaValidation:
    def test_telegram_auth_data(self):
        from app.auth.telegram import TelegramAuthData
        data = TelegramAuthData(
            id=123456,
            first_name="Test",
            last_name="User",
            auth_date=1700000000,
            hash="abc123",
        )
        assert data.id == 123456
        assert data.username is None

    def test_jwt_create_decode(self):
        from app.auth.jwt import create_access_token, decode_access_token
        token = create_access_token({"sub": "test-user-id", "tenant_id": "test-tenant", "role": "ceo"})
        payload = decode_access_token(token)
        assert payload["sub"] == "test-user-id"
        assert payload["role"] == "ceo"
        assert payload["tenant_id"] == "test-tenant"

    def test_jwt_expired_token(self):
        from datetime import timedelta
        from fastapi import HTTPException
        from app.auth.jwt import create_access_token, decode_access_token
        token = create_access_token({"sub": "test"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        assert exc_info.value.status_code == 401
