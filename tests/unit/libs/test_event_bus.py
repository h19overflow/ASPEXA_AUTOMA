"""Tests for event bus publisher and consumer."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from libs.events.publisher import (
    publish_message,
    publish_recon_request,
    publish_recon_finished,
    publish_scan_dispatch,
    publish_vuln_found,
    publish_plan_proposed,
    publish_attack_warrant,
    publish_attack_finished,
    CMD_RECON_START,
    EVT_RECON_FINISHED,
    CMD_SCAN_START,
    EVT_VULN_FOUND,
    EVT_PLAN_PROPOSED,
    CMD_ATTACK_EXECUTE,
    EVT_ATTACK_FINISHED,
    MAX_STREAM_LENGTH,
)


@pytest.mark.asyncio
class TestPublisher:
    """Test event publisher functionality."""
    
    async def test_publish_message_with_maxlen(self):
        """Test publish_message enforces maxlen."""
        with patch("libs.events.publisher.broker.publish", new_callable=AsyncMock) as mock_publish:
            payload = {"test": "data"}
            await publish_message("test_stream", payload, maxlen=5000)
            
            mock_publish.assert_called_once_with(
                payload,
                stream="test_stream",
                maxlen=5000
            )
    
    async def test_publish_message_default_maxlen(self):
        """Test publish_message uses default MAX_STREAM_LENGTH."""
        with patch("libs.events.publisher.broker.publish", new_callable=AsyncMock) as mock_publish:
            payload = {"test": "data"}
            await publish_message("test_stream", payload)
            
            mock_publish.assert_called_once_with(
                payload,
                stream="test_stream",
                maxlen=MAX_STREAM_LENGTH
            )
    
    async def test_publish_recon_request(self):
        """Test publish_recon_request publishes to correct stream."""
        with patch("libs.events.publisher.publish_message", new_callable=AsyncMock) as mock_publish:
            payload = {"audit_id": "test-123"}
            await publish_recon_request(payload)
            
            mock_publish.assert_called_once_with(CMD_RECON_START, payload)
    
    async def test_publish_recon_finished(self):
        """Test publish_recon_finished publishes to correct stream."""
        with patch("libs.events.publisher.publish_message", new_callable=AsyncMock) as mock_publish:
            payload = {"audit_id": "test-123"}
            await publish_recon_finished(payload)
            
            mock_publish.assert_called_once_with(EVT_RECON_FINISHED, payload)
    
    async def test_publish_scan_dispatch(self):
        """Test publish_scan_dispatch publishes to correct stream."""
        with patch("libs.events.publisher.publish_message", new_callable=AsyncMock) as mock_publish:
            payload = {"job_id": "scan-001"}
            await publish_scan_dispatch(payload)
            
            mock_publish.assert_called_once_with(CMD_SCAN_START, payload)
    
    async def test_publish_vuln_found(self):
        """Test publish_vuln_found publishes to correct stream."""
        with patch("libs.events.publisher.publish_message", new_callable=AsyncMock) as mock_publish:
            payload = {"cluster_id": "vuln-001"}
            await publish_vuln_found(payload)
            
            mock_publish.assert_called_once_with(EVT_VULN_FOUND, payload)
    
    async def test_publish_plan_proposed(self):
        """Test publish_plan_proposed publishes to correct stream."""
        with patch("libs.events.publisher.publish_message", new_callable=AsyncMock) as mock_publish:
            payload = {"plan_id": "plan-alpha"}
            await publish_plan_proposed(payload)
            
            mock_publish.assert_called_once_with(EVT_PLAN_PROPOSED, payload)
    
    async def test_publish_attack_warrant(self):
        """Test publish_attack_warrant publishes to correct stream."""
        with patch("libs.events.publisher.publish_message", new_callable=AsyncMock) as mock_publish:
            payload = {"warrant_id": "warrant-001"}
            await publish_attack_warrant(payload)
            
            mock_publish.assert_called_once_with(CMD_ATTACK_EXECUTE, payload)
    
    async def test_publish_attack_finished(self):
        """Test publish_attack_finished publishes to correct stream."""
        with patch("libs.events.publisher.publish_message", new_callable=AsyncMock) as mock_publish:
            payload = {"warrant_id": "warrant-001"}
            await publish_attack_finished(payload)
            
            mock_publish.assert_called_once_with(EVT_ATTACK_FINISHED, payload)
    
    async def test_max_stream_length_constant(self):
        """Test MAX_STREAM_LENGTH is set to 10000."""
        assert MAX_STREAM_LENGTH == 10000


class TestTopicConstants:
    """Test topic name constants."""
    
    def test_topic_constants_defined(self):
        """Test all topic constants are properly defined."""
        assert CMD_RECON_START == "cmd_recon_start"
        assert EVT_RECON_FINISHED == "evt_recon_finished"
        assert CMD_SCAN_START == "cmd_scan_start"
        assert EVT_VULN_FOUND == "evt_vuln_found"
        assert EVT_PLAN_PROPOSED == "evt_plan_proposed"
        assert CMD_ATTACK_EXECUTE == "cmd_attack_execute"
        assert EVT_ATTACK_FINISHED == "evt_attack_finished"
