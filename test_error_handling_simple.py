#!/usr/bin/env python3
"""
简化的错误处理测试
"""
from xray_gui.core.error_handler import (
    ErrorHandler, 
    ErrorInfo, 
    ErrorSeverity, 
    ErrorCategory,
    handle_error,
    handle_exception,
    error_handler_decorator
)

def test_error_handling_graceful_degradation():
    """测试错误处理的优雅降级"""
    print("Testing error handling graceful degradation...")
    
    error_handler = ErrorHandler()
    
    # 测试各种错误情况
    test_cases = [
        {
            'category': ErrorCategory.PROTOCOL_PARSING,
            'code': 'protocol_parsing_invalid_link',
            'message': '无效的协议链接格式',
            'details': 'vmess://invalid-base64-content',
            'context': {'link': 'vmess://invalid', 'parser': 'VMess'}
        },
        {
            'category': ErrorCategory.XRAY_SERVICE,
            'code': 'xray_service_start_failed',
            'message': 'Xray服务启动失败',
            'details': 'Process exited with code 1',
            'context': {'config_path': '/tmp/config.json', 'port': 8080}
        },
        {
            'category': ErrorCategory.LATENCY_TEST,
            'code': 'latency_test_timeout',
            'message': '延迟测试超时',
            'details': 'Connection timeout after 5 seconds',
            'context': {'node': 'test-node', 'timeout': 5}
        },
        {
            'category': ErrorCategory.STARTUP_MANAGEMENT,
            'code': 'startup_management_registry_access_denied',
            'message': '注册表访问被拒绝',
            'details': 'Access denied to HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',
            'context': {'registry_key': 'XrayManager', 'operation': 'write'}
        },
        {
            'category': ErrorCategory.PORT_ALLOCATION,
            'code': 'port_allocation_port_in_use',
            'message': '端口已被占用',
            'details': 'Port 8080 is already in use by another process',
            'context': {'port': 8080, 'process': 'chrome.exe'}
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"  Testing case {i+1}: {test_case['code']}")
        
        try:
            # 处理错误应该不会抛出异常
            error_info = error_handler.handle_error(**test_case)
            
            # 验证错误信息对象的完整性
            assert isinstance(error_info, ErrorInfo), "应该返回ErrorInfo对象"
            assert error_info.category == test_case['category'], "错误类别应该正确"
            assert error_info.code == test_case['code'], "错误代码应该正确"
            assert error_info.message is not None, "应该总是有消息"
            assert error_info.timestamp is not None, "应该总是有时间戳"
            assert isinstance(error_info.severity, ErrorSeverity), "严重程度应该是ErrorSeverity类型"
            
            # 验证用户消息
            user_message = error_info.to_user_message()
            assert isinstance(user_message, str), "用户消息应该是字符串"
            assert len(user_message) > 0, "用户消息不应该为空"
            assert error_info.severity.value.upper() in user_message, "用户消息应该包含严重程度"
            assert error_info.message in user_message, "用户消息应该包含错误消息"
            
            print(f"    ✅ {test_case['code']} 处理成功")
            
        except Exception as e:
            print(f"    ❌ {test_case['code']} 处理失败: {e}")
            raise
    
    print("✅ 错误处理优雅降级测试通过")

def test_exception_handling():
    """测试异常处理"""
    print("\nTesting exception handling...")
    
    error_handler = ErrorHandler()
    
    # 测试各种异常类型
    exceptions = [
        ValueError("Invalid value provided"),
        RuntimeError("Runtime error occurred"),
        FileNotFoundError("Configuration file not found"),
        PermissionError("Permission denied"),
        ConnectionError("Network connection failed"),
        TimeoutError("Operation timed out")
    ]
    
    for exception in exceptions:
        exception_type = type(exception).__name__
        print(f"  Testing {exception_type}...")
        
        try:
            error_info = error_handler.handle_exception(
                category=ErrorCategory.UNKNOWN,
                exception=exception,
                context={'test': True}
            )
            
            # 验证异常处理结果
            assert isinstance(error_info, ErrorInfo), "应该返回ErrorInfo对象"
            assert error_info.category == ErrorCategory.UNKNOWN, "错误类别应该正确"
            assert exception_type.lower() in error_info.code, "错误代码应该包含异常类型"
            assert str(exception) in error_info.message, "错误消息应该包含异常消息"
            assert error_info.details is not None, "应该有详细信息"
            assert exception_type in error_info.details, "详细信息应该包含异常类型"
            
            print(f"    ✅ {exception_type} 处理成功")
            
        except Exception as e:
            print(f"    ❌ {exception_type} 处理失败: {e}")
            raise
    
    print("✅ 异常处理测试通过")

def test_error_history_management():
    """测试错误历史记录管理"""
    print("\nTesting error history management...")
    
    error_handler = ErrorHandler()
    
    # 生成多个错误
    num_errors = 10
    for i in range(num_errors):
        error_handler.handle_error(
            category=ErrorCategory.PROTOCOL_PARSING,
            code=f"test_error_{i}",
            message=f"Test error message {i}"
        )
    
    # 验证历史记录
    history = error_handler.get_error_history()
    assert len(history) == num_errors, f"历史记录数量应该是{num_errors}，实际是{len(history)}"
    
    # 验证按类别过滤
    category_history = error_handler.get_error_history(category=ErrorCategory.PROTOCOL_PARSING)
    assert len(category_history) == num_errors, "按类别过滤的历史记录数量应该正确"
    
    # 验证限制数量
    limited_history = error_handler.get_error_history(limit=5)
    assert len(limited_history) <= 5, "限制数量的历史记录应该不超过5个"
    
    # 验证统计信息
    stats = error_handler.get_error_statistics()
    assert stats['total_errors'] == num_errors, "统计信息中的总错误数应该正确"
    assert ErrorCategory.PROTOCOL_PARSING.value in stats['by_category'], "统计信息应该包含按类别的统计"
    assert stats['by_category'][ErrorCategory.PROTOCOL_PARSING.value] == num_errors, "按类别的统计数量应该正确"
    
    print("✅ 错误历史记录管理测试通过")

def test_error_callback_system():
    """测试错误回调系统"""
    print("\nTesting error callback system...")
    
    error_handler = ErrorHandler()
    callback_called = False
    callback_error_info = None
    
    def test_callback(error_info):
        nonlocal callback_called, callback_error_info
        callback_called = True
        callback_error_info = error_info
    
    # 注册回调
    test_category = ErrorCategory.XRAY_SERVICE
    error_handler.register_error_callback(test_category, test_callback)
    
    # 触发错误
    error_info = error_handler.handle_error(
        category=test_category,
        code="test_callback",
        message="Test callback message"
    )
    
    # 验证回调被调用
    assert callback_called, "回调应该被调用"
    assert callback_error_info is not None, "回调应该接收到错误信息"
    assert callback_error_info.code == "test_callback", "回调接收的错误信息应该正确"
    
    # 重置回调状态
    callback_called = False
    callback_error_info = None
    
    # 触发不同类别的错误，不应该调用回调
    error_handler.handle_error(
        category=ErrorCategory.LATENCY_TEST,
        code="test_no_callback",
        message="Test no callback message"
    )
    
    # 验证回调没有被调用
    assert not callback_called, "不同类别的错误不应该触发回调"
    assert callback_error_info is None, "不应该接收到错误信息"
    
    print("✅ 错误回调系统测试通过")

def test_error_decorator():
    """测试错误处理装饰器"""
    print("\nTesting error decorator...")
    
    error_handler = ErrorHandler()
    
    @error_handler_decorator(ErrorCategory.CONFIG_PERSISTENCE)
    def test_function_that_raises():
        raise ValueError("Test exception from decorated function")
    
    @error_handler_decorator(ErrorCategory.CONFIG_PERSISTENCE)
    def test_function_that_succeeds():
        return "success"
    
    # 测试成功的函数
    result = test_function_that_succeeds()
    assert result == "success", "成功的函数应该返回正确结果"
    
    # 测试抛出异常的函数
    try:
        test_function_that_raises()
        assert False, "应该抛出异常"
    except ValueError as e:
        assert str(e) == "Test exception from decorated function", "异常消息应该正确"
    
    # 验证错误被记录（使用全局错误处理器）
    from xray_gui.core.error_handler import global_error_handler
    history = global_error_handler.get_error_history(category=ErrorCategory.CONFIG_PERSISTENCE)
    assert len(history) > 0, "装饰器应该记录错误"
    
    # 查找装饰器记录的错误
    decorator_error = None
    for error in history:
        if error.context and "test_function_that_raises" in str(error.context):
            decorator_error = error
            break
    
    assert decorator_error is not None, "应该找到装饰器记录的错误"
    assert "ValueError" in decorator_error.message, "错误消息应该包含异常类型"
    assert "Test exception from decorated function" in decorator_error.message, "错误消息应该包含异常消息"
    
    print("✅ 错误处理装饰器测试通过")

def test_global_error_functions():
    """测试全局错误处理函数"""
    print("\nTesting global error functions...")
    
    # 测试全局错误处理函数
    error_info = handle_error(
        category=ErrorCategory.NETWORK_CONNECTION,
        code="test_global_error",
        message="Test global error message"
    )
    
    assert isinstance(error_info, ErrorInfo), "应该返回ErrorInfo对象"
    assert error_info.category == ErrorCategory.NETWORK_CONNECTION, "错误类别应该正确"
    assert error_info.code == "test_global_error", "错误代码应该正确"
    assert error_info.message == "Test global error message", "错误消息应该正确"
    
    # 测试全局异常处理函数
    test_exception = RuntimeError("Test global exception")
    exception_info = handle_exception(
        category=ErrorCategory.SYSTEM_PERMISSION,
        exception=test_exception
    )
    
    assert isinstance(exception_info, ErrorInfo), "应该返回ErrorInfo对象"
    assert exception_info.category == ErrorCategory.SYSTEM_PERMISSION, "错误类别应该正确"
    assert "RuntimeError" in exception_info.message, "错误消息应该包含异常类型"
    assert "Test global exception" in exception_info.message, "错误消息应该包含异常消息"
    
    print("✅ 全局错误处理函数测试通过")

def test_predefined_error_definitions():
    """测试预定义错误定义"""
    print("\nTesting predefined error definitions...")
    
    error_handler = ErrorHandler()
    
    # 测试一些预定义的错误代码
    predefined_codes = [
        'protocol_parsing_invalid_link',
        'xray_service_start_failed',
        'latency_test_timeout',
        'startup_management_registry_access_denied',
        'port_allocation_port_in_use',
        'config_persistence_file_corrupted'
    ]
    
    for code in predefined_codes:
        print(f"  Testing predefined error: {code}")
        
        error_info = error_handler.handle_error(
            category=ErrorCategory.UNKNOWN,
            code=code
        )
        
        # 验证预定义错误有合适的消息和建议
        assert error_info.message is not None, "预定义错误应该有消息"
        assert len(error_info.message) > 0, "预定义错误消息不应该为空"
        assert isinstance(error_info.severity, ErrorSeverity), "预定义错误应该有严重程度"
        
        # 大多数预定义错误应该有建议
        if error_info.suggestions:
            assert isinstance(error_info.suggestions, list), "建议应该是列表"
            assert len(error_info.suggestions) > 0, "建议列表不应该为空"
            for suggestion in error_info.suggestions:
                assert isinstance(suggestion, str), "建议应该是字符串"
                assert len(suggestion) > 0, "建议不应该为空"
        
        print(f"    ✅ {code} 验证成功")
    
    print("✅ 预定义错误定义测试通过")

if __name__ == "__main__":
    print("🧪 开始错误处理属性测试...")
    
    test_error_handling_graceful_degradation()
    test_exception_handling()
    test_error_history_management()
    test_error_callback_system()
    test_error_decorator()
    test_global_error_functions()
    test_predefined_error_definitions()
    
    print("\n🎉 所有错误处理属性测试都通过了！")