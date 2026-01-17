"""
Unit tests for gateway factory functions.
Tests the create_gateway_handler and create_mass_handler factory pattern.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.handlers.gateways import (
    extract_card_input,
    create_gateway_handler,
    create_mass_handler
)


class TestExtractCardInput:
    """Tests for extract_card_input function."""
    
    def test_extract_with_prefix(self):
        """Test extracting card input when message starts with command prefix."""
        update = Mock()
        update.message.text = '/sa1 4111111111111111|12|25|123'
        context = Mock()
        context.args = []
        
        result = extract_card_input(update, context, ['/sa1 '])
        assert result == '4111111111111111|12|25|123'
    
    def test_extract_with_newline(self):
        """Test extracting card input from multiline message."""
        update = Mock()
        update.message.text = '/sa1\n4111111111111111|12|25|123'
        context = Mock()
        context.args = []
        
        result = extract_card_input(update, context, ['/sa1 '])
        assert result == '4111111111111111|12|25|123'
    
    def test_extract_with_args(self):
        """Test extracting card input from command args."""
        update = Mock()
        update.message.text = '/sa1'
        context = Mock()
        context.args = ['4111111111111111|12|25|123']
        
        result = extract_card_input(update, context, ['/sa1 '])
        assert result == '4111111111111111|12|25|123'
    
    def test_extract_empty(self):
        """Test extracting returns empty when no input provided."""
        update = Mock()
        update.message.text = '/sa1'
        context = Mock()
        context.args = []
        
        result = extract_card_input(update, context, ['/sa1 '])
        assert result == ''
    
    def test_extract_case_insensitive_prefix(self):
        """Test prefix matching is case-insensitive."""
        update = Mock()
        update.message.text = '/SA1 4111111111111111|12|25|123'
        context = Mock()
        context.args = []
        
        result = extract_card_input(update, context, ['/sa1 '])
        assert result == '4111111111111111|12|25|123'


class TestCreateGatewayHandler:
    """Tests for create_gateway_handler factory."""
    
    @pytest.mark.asyncio
    async def test_factory_creates_callable(self):
        """Test factory returns an async callable."""
        gateway_fn = Mock()
        process_fn = AsyncMock()
        
        handler = create_gateway_handler(
            gateway_fn, 
            "Test Gateway", 
            "test", 
            ['/test '],
            process_fn
        )
        
        assert callable(handler)
    
    @pytest.mark.asyncio
    async def test_handler_calls_process_fn(self):
        """Test generated handler calls process function with correct args."""
        gateway_fn = Mock()
        process_fn = AsyncMock()
        
        handler = create_gateway_handler(
            gateway_fn,
            "Test Gateway",
            "test",
            ['/test '],
            process_fn
        )
        
        update = Mock()
        update.message.text = '/test 4111111111111111|12|25|123'
        context = Mock()
        context.args = []
        
        await handler(update, context)
        
        process_fn.assert_called_once_with(
            update,
            '4111111111111111|12|25|123',
            gateway_fn,
            "Test Gateway",
            "test"
        )


class TestCreateMassHandler:
    """Tests for create_mass_handler factory."""
    
    @pytest.mark.asyncio
    async def test_mass_factory_creates_callable(self):
        """Test mass factory returns an async callable."""
        gateway_fn = Mock()
        mass_fn = AsyncMock()
        
        handler = create_mass_handler(gateway_fn, "Test Gateway", mass_fn)
        
        assert callable(handler)
    
    @pytest.mark.asyncio
    async def test_mass_handler_calls_mass_fn(self):
        """Test generated mass handler calls mass function correctly."""
        gateway_fn = Mock()
        mass_fn = AsyncMock()
        
        handler = create_mass_handler(gateway_fn, "Test Gateway", mass_fn)
        
        update = Mock()
        context = Mock()
        
        await handler(update, context)
        
        mass_fn.assert_called_once_with(
            update, 
            context, 
            gateway_fn=gateway_fn, 
            gateway_name="Test Gateway"
        )


class TestCardParsing:
    """Tests for card format parsing utilities."""
    
    def test_parse_standard_format(self):
        """Test parsing CARD|MM|YY|CVV format."""
        card_input = "5598880393880150|04|2036|346"
        parts = card_input.split('|')
        
        assert len(parts) == 4
        assert parts[0] == "5598880393880150"
        assert parts[1] == "04"
        assert parts[2] == "2036"
        assert parts[3] == "346"
    
    def test_parse_short_year(self):
        """Test extracting last 2 digits of year."""
        card_input = "5598880393880150|04|2036|346"
        parts = card_input.split('|')
        year = parts[2][-2:]
        
        assert year == "36"
    
    def test_parse_multiple_cards(self):
        """Test parsing multiple cards from batch input."""
        batch = """5598880393880150|04|2036|346
5598880393888070|07|2029|518
5598880393880549|08|2035|821"""
        
        cards = [line.strip() for line in batch.strip().split('\n') if line.strip()]
        
        assert len(cards) == 3
        assert cards[0] == "5598880393880150|04|2036|346"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
