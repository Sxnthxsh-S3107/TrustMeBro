import pytest
import base64
from unittest.mock import patch, MagicMock
from voice_intake.app.asr import AI4BharatASRService, get_asr_service


def test_ai4bharat_missing_api_key(monkeypatch):
    """Test that ValueError is raised if AI4BHARAT_API_KEY is not configured."""
    monkeypatch.delenv("AI4BHARAT_API_KEY", raising=False)
    monkeypatch.delenv("BHASHINI_API_KEY", raising=False)
    
    service = AI4BharatASRService(api_key=None)
    with pytest.raises(ValueError, match="AI4BHARAT_API_KEY is not configured"):
        service.transcribe(b"dummy audio content" * 10, language="ta")


def test_ai4bharat_short_audio():
    """Test that ValueError is raised if audio is too short."""
    service = AI4BharatASRService(api_key="test_key")
    with pytest.raises(ValueError, match="Audio recording is empty or too short"):
        service.transcribe(b"too short", language="en")


def test_ai4bharat_transcription_success():
    """Test successful AI4Bharat transcription parsing Dhruva response format."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "pipelineResponse": [
            {
                "taskType": "asr",
                "output": [
                    {
                        "source": "எனக்கு நெஞ்சு வலி மற்றும் காய்ச்சல் உள்ளது"
                    }
                ]
            }
        ]
    }

    dummy_audio = b"RIFF" + b"x" * 200

    with patch("requests.post", return_value=mock_response) as mock_post:
        service = AI4BharatASRService(api_key="mock_ai4bharat_key", user_id="mock_user")
        result = service.transcribe(dummy_audio, language="ta", filename="test.wav")

        assert result == "எனக்கு நெஞ்சு வலி மற்றும் காய்ச்சல் உள்ளது"
        mock_post.assert_called_once()
        
        # Verify headers and payload
        args, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "mock_ai4bharat_key"
        assert kwargs["headers"]["userID"] == "mock_user"
        
        payload = kwargs["json"]
        assert payload["pipelineTasks"][0]["config"]["language"]["sourceLanguage"] == "ta"
        assert payload["inputData"]["audio"][0]["audioContent"] == base64.b64encode(dummy_audio).decode("utf-8")


def test_get_asr_service_ai4bharat_factory(monkeypatch):
    """Test factory resolution for ai4bharat backend."""
    monkeypatch.setenv("ASR_BACKEND", "ai4bharat")
    monkeypatch.setenv("AI4BHARAT_API_KEY", "dummy_key")
    
    service = get_asr_service()
    assert isinstance(service, AI4BharatASRService)
