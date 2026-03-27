"""Tests for the exceptions module."""

import pytest
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from template_agent.src.core.exceptions.exceptions import (
    AppException,
    AppExceptionCode,
    ForbiddenException,
    ToolCallException,
    UnauthorizedException,
)


class TestAppException:
    """Test cases for AppException class."""

    def test_creation_with_default_code(self):
        """Test creating AppException with default exception code."""
        exception = AppException("Something went wrong")
        assert exception.detail_message == "Something went wrong"
        assert exception.response_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert exception.message == "Internal Server Error"
        assert exception.error_code == "E_003"

    def test_creation_with_custom_code(self):
        """Test creating AppException with custom exception code."""
        exception = AppException("Invalid request", AppExceptionCode.BAD_REQUEST_ERROR)
        assert exception.detail_message == "Invalid request"
        assert exception.response_code == HTTP_400_BAD_REQUEST
        assert exception.message == "Bad Request"
        assert exception.error_code == "E_001"

    def test_str_representation(self):
        """Test string representation of AppException."""
        exception = AppException("Invalid request", AppExceptionCode.BAD_REQUEST_ERROR)
        expected = "response_code=400, message=Bad Request, detail_message=Invalid request, error_code=E_001"
        assert str(exception) == expected


class TestToolCallException:
    """Test cases for ToolCallException class."""

    def test_creation(self):
        """Test creating ToolCallException."""
        exception = ToolCallException("Tool execution failed")
        assert exception.detail_message == "Tool execution failed"
        assert exception.response_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert exception.error_code == "E_006"
        assert isinstance(exception, AppException)


class TestUnauthorizedException:
    """Test cases for UnauthorizedException class."""

    def test_creation(self):
        """Test creating UnauthorizedException."""
        exception = UnauthorizedException("Invalid credentials")
        assert exception.detail_message == "Invalid credentials"
        assert exception.response_code == HTTP_401_UNAUTHORIZED
        assert exception.error_code == "E_004"
        assert isinstance(exception, AppException)


class TestForbiddenException:
    """Test cases for ForbiddenException class."""

    def test_creation(self):
        """Test creating ForbiddenException."""
        exception = ForbiddenException("Access denied")
        assert exception.detail_message == "Access denied"
        assert exception.response_code == HTTP_403_FORBIDDEN
        assert exception.error_code == "E_005"
        assert isinstance(exception, AppException)
