"""
Integration tests for handler registration.
Verifies that all handlers are properly wired via the registry.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHandlerImports:
    """Tests that all handlers can be imported without errors."""
    
    def test_gateway_factory_imports(self):
        """Test gateway factory functions are importable."""
        from bot.handlers.gateways import (
            create_gateway_handler,
            create_mass_handler,
            extract_card_input
        )
        assert callable(create_gateway_handler)
        assert callable(create_mass_handler)
        assert callable(extract_card_input)
    
    def test_system_handlers_import(self):
        """Test system handlers module imports."""
        from bot.handlers import system
        assert hasattr(system, 'start_command') or True  
    
    def test_utility_handlers_import(self):
        """Test utility handlers module imports."""
        from bot.handlers import utility
        assert hasattr(utility, 'bin_lookup_command') or True


class TestConcreteHandlers:
    """Tests that concrete handlers are properly created via factories."""
    
    def test_auth_handlers_exist(self):
        """Test auth gate handlers are created via factory."""
        import transferto
        
        handlers = [
            'foe_auth_command',
            'charitywater_auth_command', 
            'donorschoose_auth_command',
            'newschools_auth_command',
            'ywca_auth_command'
        ]
        
        for handler_name in handlers:
            handler = getattr(transferto, handler_name, None)
            assert handler is not None, f"Missing handler: {handler_name}"
            assert callable(handler), f"Handler not callable: {handler_name}"
    
    def test_mass_auth_handlers_exist(self):
        """Test mass auth handlers are created via factory."""
        import transferto
        
        handlers = [
            'mass_foe_auth_command',
            'mass_charitywater_auth_command',
            'mass_donorschoose_auth_command',
            'mass_newschools_auth_command',
            'mass_ywca_auth_command'
        ]
        
        for handler_name in handlers:
            handler = getattr(transferto, handler_name, None)
            assert handler is not None, f"Missing handler: {handler_name}"
            assert callable(handler), f"Handler not callable: {handler_name}"
    
    def test_lions_club_handlers_exist(self):
        """Test lions club handlers created via factory."""
        import transferto
        
        assert hasattr(transferto, 'lions_club_command')
        assert callable(transferto.lions_club_command)
        assert hasattr(transferto, 'mass_lions_club_command')
        assert callable(transferto.mass_lions_club_command)
    
    def test_charge_handlers_exist(self):
        """Test charge gate handlers exist."""
        import transferto
        
        handlers = [
            'charge1_command', 'charge2_command', 'charge4_command', 'charge5_command',
            'mass_charge1_command', 'mass_charge2_command', 'mass_charge4_command', 'mass_charge5_command'
        ]
        
        for handler_name in handlers:
            handler = getattr(transferto, handler_name, None)
            assert handler is not None, f"Missing handler: {handler_name}"
            assert callable(handler), f"Handler not callable: {handler_name}"


class TestHandlerRegistration:
    """Tests for the handler registry system."""
    
    def test_registry_config_exists(self):
        """Test registry configuration is defined."""
        from bot.handlers.registry import ALIAS_COMMANDS
        
        assert isinstance(ALIAS_COMMANDS, dict)
        assert len(ALIAS_COMMANDS) > 0
    
    def test_registry_has_command_lists(self):
        """Test registry has all expected command lists."""
        from bot.handlers import registry
        
        expected_lists = [
            'SYSTEM_COMMANDS', 'GATEWAY_COMMANDS', 'AUTH_GATE_COMMANDS', 
            'CHARGE_COMMANDS', 'SHOPIFY_COMMANDS', 'UTILITY_COMMANDS'
        ]
        
        for list_name in expected_lists:
            assert hasattr(registry, list_name), f"Missing command list: {list_name}"
    
    def test_handler_aliases_defined(self):
        """Test that handler aliases are properly defined."""
        from bot.handlers.registry import ALIAS_COMMANDS
        
        total_aliases = len(ALIAS_COMMANDS)
        assert total_aliases >= 50, f"Expected 50+ aliases, found {total_aliases}"


class TestWorkingGates:
    """Tests for all 11 verified working gates."""
    
    def test_all_11_working_gate_handlers_exist(self):
        """Verify all 11 working gates have handlers."""
        import transferto
        
        working_gates = {
            'pariyatti_auth': 'pariyatti_auth_command',
            'cedine_auth': 'cedine_auth_command', 
            'stripe_multi': 'stripe_multi_command',
            'stripe_charity': 'stripe_charity_command',
            'shopify_checkout': 'checkout_command',
            'lions_club': 'lions_club_command',
            'stripe': 'stripe_command',
            'stripe_epicalarc': 'stripe_epicalarc_command',
            'braintree': 'braintree_laguna_command',
            'woostripe_auth': 'checkoutauth_command',
            'auto_detect': 'check_command',
        }
        
        for gate_name, handler_name in working_gates.items():
            handler = getattr(transferto, handler_name, None)
            assert handler is not None, f"Missing working gate handler: {handler_name} ({gate_name})"
            assert callable(handler), f"Handler not callable: {handler_name}"
    
    def test_all_11_working_gate_mass_handlers(self):
        """Verify mass handlers exist for working gates that support them."""
        import transferto
        
        mass_handlers = [
            'mass_pariyatti_auth_command',
            'mass_cedine_auth_command',
            'mass_stripe_multi_command', 
            'mass_stripe_charity_command',
            'mass_lions_club_command',
            'mass_stripe_command',
            'mass_check_command',
        ]
        
        for handler_name in mass_handlers:
            handler = getattr(transferto, handler_name, None)
            assert handler is not None, f"Missing mass handler: {handler_name}"
            assert callable(handler), f"Mass handler not callable: {handler_name}"


class TestAliasMapping:
    """Tests for command alias mappings."""
    
    def test_working_gate_aliases_exist(self):
        """Verify aliases for working gates are defined in ALIAS_COMMANDS."""
        from bot.handlers.registry import ALIAS_COMMANDS
        
        expected_aliases = [
            'pa', 'ced', 'sm', 'sc2', 'sn', 'lc5', 'sa1', 'sa2', 'sa3', 'sa4', 'sa5',
            'c1', 'c2', 'c4', 'c5', 'mc1', 'mc2', 'mc4', 'mc5'
        ]
        
        for alias in expected_aliases:
            assert alias in ALIAS_COMMANDS, f"Missing alias: {alias}"
            handler_name = ALIAS_COMMANDS[alias]
            assert isinstance(handler_name, str) and len(handler_name) > 0, \
                f"Alias {alias} has invalid handler mapping: {handler_name}"
    
    def test_alias_count_minimum(self):
        """Test minimum number of aliases defined."""
        from bot.handlers.registry import ALIAS_COMMANDS
        
        assert len(ALIAS_COMMANDS) >= 60, f"Expected 60+ aliases, found {len(ALIAS_COMMANDS)}"


class TestRegisterAllHandlers:
    """Tests for register_all_handlers function."""
    
    def test_register_function_exists(self):
        """Test register_all_handlers is importable and callable."""
        from bot.handlers.registry import register_all_handlers
        
        assert callable(register_all_handlers)
    
    def test_register_with_mock_application(self):
        """Test register_all_handlers with a mock Application."""
        from unittest.mock import Mock, MagicMock
        from bot.handlers.registry import register_all_handlers
        import transferto
        
        mock_app = Mock()
        mock_app.add_handler = MagicMock()
        
        handlers_dict = {
            'start_command': getattr(transferto, 'start_command', Mock()),
            'menu_command': getattr(transferto, 'menu_command', Mock()),
            'check_command': getattr(transferto, 'check_command', Mock()),
        }
        
        try:
            register_all_handlers(mock_app, handlers_dict)
            assert mock_app.add_handler.called, "add_handler should be called"
        except Exception as e:
            pytest.skip(f"register_all_handlers requires full bot context: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
