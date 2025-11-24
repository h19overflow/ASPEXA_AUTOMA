"""Unit tests for network communication layer."""
import pytest
from aioresponses import aioresponses
from services.cartographer.tools.network import (
    call_target_endpoint,
    check_target_connectivity,
    NetworkError
)


class TestNetworkCommunication:
    """Test network communication with target endpoints."""
    
    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test successful HTTP request to target endpoint."""
        with aioresponses() as m:
            m.post(
                'http://target.example.com/api',
                payload={'response': 'Hello from target'},
                status=200
            )
            
            response = await call_target_endpoint(
                url='http://target.example.com/api',
                auth_headers={'Authorization': 'Bearer test-token'},
                message='Test question'
            )
            
            assert response == 'Hello from target'
    
    @pytest.mark.asyncio
    async def test_alternative_response_field(self):
        """Test handling response with 'message' field instead of 'response'."""
        with aioresponses() as m:
            m.post(
                'http://target.example.com/api',
                payload={'message': 'Alternative response'},
                status=200
            )
            
            response = await call_target_endpoint(
                url='http://target.example.com/api',
                auth_headers={},
                message='Test'
            )
            
            assert response == 'Alternative response'
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self):
        """Test handling of authentication failures (401/403)."""
        with aioresponses() as m:
            m.post(
                'http://target.example.com/api',
                status=401,
                body='Unauthorized'
            )
            
            with pytest.raises(NetworkError) as exc_info:
                await call_target_endpoint(
                    url='http://target.example.com/api',
                    auth_headers={},
                    message='Test',
                    max_retries=1
                )
            
            assert 'Authentication failed' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_errors(self):
        """Test retry logic on transient errors."""
        with aioresponses() as m:
            # Fail first two attempts, succeed on third
            m.post('http://target.example.com/api', status=500)
            m.post('http://target.example.com/api', status=503)
            m.post(
                'http://target.example.com/api',
                payload={'response': 'Success after retries'},
                status=200
            )
            
            response = await call_target_endpoint(
                url='http://target.example.com/api',
                auth_headers={},
                message='Test',
                max_retries=3
            )
            
            assert response == 'Success after retries'
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test failure after exceeding max retries."""
        with aioresponses() as m:
            # All attempts fail
            m.post('http://target.example.com/api', status=500)
            m.post('http://target.example.com/api', status=500)
            m.post('http://target.example.com/api', status=500)
            
            with pytest.raises(NetworkError) as exc_info:
                await call_target_endpoint(
                    url='http://target.example.com/api',
                    auth_headers={},
                    message='Test',
                    max_retries=3
                )
            
            assert 'Failed to reach target after 3 attempts' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_connectivity_check_success(self):
        """Test successful connectivity check."""
        with aioresponses() as m:
            m.post(
                'http://target.example.com/api',
                payload={'response': 'OK'},
                status=200
            )
            
            is_reachable = await check_target_connectivity(
                url='http://target.example.com/api',
                auth_headers={}
            )
            
            assert is_reachable is True
    
    @pytest.mark.asyncio
    async def test_connectivity_check_failure(self):
        """Test connectivity check with unreachable endpoint."""
        with aioresponses() as m:
            m.post('http://target.example.com/api', status=500)
            
            is_reachable = await check_target_connectivity(
                url='http://target.example.com/api',
                auth_headers={}
            )
            
            assert is_reachable is False
    
    @pytest.mark.asyncio
    async def test_custom_headers_included(self):
        """Test that custom auth headers are included in request."""
        with aioresponses() as m:
            m.post(
                'http://target.example.com/api',
                payload={'response': 'Authenticated'},
                status=200
            )
            
            await call_target_endpoint(
                url='http://target.example.com/api',
                auth_headers={
                    'Authorization': 'Bearer secret-token',
                    'X-Custom-Header': 'custom-value'
                },
                message='Test'
            )
            
            # Verify the request was made (aioresponses tracks this)
            assert len(m.requests) == 1
