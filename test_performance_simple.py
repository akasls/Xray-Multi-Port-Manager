#!/usr/bin/env python3
"""
简化的性能优化测试
"""
import asyncio
import time
import threading
from unittest.mock import Mock, patch

from xray_gui.core.concurrent_latency_tester import (
    ConcurrentLatencyTester, 
    ConcurrentTestConfig, 
    TestStrategy,
    BatchTestResult
)
from xray_gui.core.system_adaptability_manager import (
    SystemAdaptabilityManager,
    SystemState,
    SystemEvent,
    AdaptationRule
)
from xray_gui.core.node import Node

def test_concurrent_processing_efficiency():
    """测试并发处理效率性"""
    print("Testing concurrent processing efficiency...")
    
    concurrent_tester = ConcurrentLatencyTester()
    
    # 创建测试节点
    node_count = 10
    nodes = []
    for i in range(node_count):
        node = Node(
            uuid=f"test-uuid-{i}",
            remark=f"test_node_{i}",
            protocol="vless",
            address="127.0.0.1",
            port=443 + i
        )
        nodes.append(node)
    
    # 配置并发测试
    config = ConcurrentTestConfig(
        max_concurrent=5,
        timeout=1.0,  # 短超时以加快测试
        strategy=TestStrategy.THREADING
    )
    
    print(f"  Testing {node_count} nodes with max_concurrent={config.max_concurrent}")
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行并发测试
    result = concurrent_tester.test_nodes_threaded(
        nodes=nodes,
        config=config
    )
    
    # 记录结束时间
    end_time = time.time()
    test_duration = end_time - start_time
    
    # 验证并发处理效率
    assert isinstance(result, BatchTestResult), "应该返回BatchTestResult对象"
    assert result.total_nodes == node_count, f"总节点数应该是{node_count}，实际是{result.total_nodes}"
    assert len(result.results) == node_count, f"结果数量应该是{node_count}，实际是{len(result.results)}"
    
    # 验证并发效率：并发测试应该比串行测试快
    expected_serial_time = node_count * config.timeout
    efficiency_ratio = expected_serial_time / test_duration
    
    print(f"  并发测试用时: {test_duration:.2f}s")
    print(f"  预期串行用时: {expected_serial_time:.2f}s")
    print(f"  效率比: {efficiency_ratio:.2f}x")
    
    # 并发效率应该至少是串行的1.5倍（考虑到测试环境的限制）
    assert efficiency_ratio > 1.5, f"并发效率不足：效率比{efficiency_ratio:.2f}应该大于1.5"
    
    # 验证结果完整性
    for i, test_result in enumerate(result.results):
        assert test_result.node_uuid == f"test-uuid-{i}", f"节点UUID应该匹配"
        assert test_result.timestamp is not None, "应该有时间戳"
        assert test_result.latency is not None, "应该有延迟结果（可能是-1表示失败）"
    
    # 验证统计信息
    result.update_statistics()
    assert result.total_nodes == node_count, "统计信息中的总节点数应该正确"
    assert result.completed_nodes >= 0, "完成节点数应该非负"
    assert result.test_duration >= 0, "测试持续时间应该非负"
    
    print("✅ 并发处理效率性测试通过")

def test_async_vs_threading_strategies():
    """测试异步和线程策略的效率对比"""
    print("\nTesting async vs threading strategies...")
    
    concurrent_tester = ConcurrentLatencyTester()
    
    # 创建测试节点
    nodes = []
    for i in range(8):
        node = Node(
            uuid=f"strategy-test-{i}",
            remark=f"strategy_node_{i}",
            protocol="vless",
            address="127.0.0.1",
            port=8000 + i
        )
        nodes.append(node)
    
    config = ConcurrentTestConfig(
        max_concurrent=4,
        timeout=0.5,
    )
    
    # 测试线程策略
    print("  Testing threading strategy...")
    config.strategy = TestStrategy.THREADING
    start_time = time.time()
    threading_result = concurrent_tester.test_nodes_threaded(nodes=nodes, config=config)
    threading_duration = time.time() - start_time
    
    # 测试异步策略
    print("  Testing async strategy...")
    config.strategy = TestStrategy.ASYNCIO
    start_time = time.time()
    async_result = asyncio.run(concurrent_tester.test_nodes_async(nodes=nodes, config=config))
    async_duration = time.time() - start_time
    
    print(f"  线程策略用时: {threading_duration:.2f}s")
    print(f"  异步策略用时: {async_duration:.2f}s")
    
    # 验证两种策略都能正常工作
    assert isinstance(threading_result, BatchTestResult), "线程策略应该返回BatchTestResult"
    assert isinstance(async_result, BatchTestResult), "异步策略应该返回BatchTestResult"
    assert len(threading_result.results) == len(nodes), "线程策略结果数量应该正确"
    assert len(async_result.results) == len(nodes), "异步策略结果数量应该正确"
    
    # 两种策略的效率都应该合理
    max_expected_time = len(nodes) * config.timeout * 0.8  # 并发应该至少快20%
    assert threading_duration < max_expected_time, f"线程策略效率不足：{threading_duration:.2f}s > {max_expected_time:.2f}s"
    assert async_duration < max_expected_time, f"异步策略效率不足：{async_duration:.2f}s > {max_expected_time:.2f}s"
    
    print("✅ 策略效率对比测试通过")

def test_system_adaptability():
    """测试系统适应性"""
    print("\nTesting system adaptability...")
    
    adaptability_manager = SystemAdaptabilityManager()
    
    # 创建测试适应规则
    rule_triggered = False
    rule_exception_occurred = False
    
    def test_adaptation_action(state: SystemState):
        nonlocal rule_triggered
        rule_triggered = True
        print("    适应规则被触发")
    
    def failing_adaptation_action(state: SystemState):
        nonlocal rule_exception_occurred
        rule_exception_occurred = True
        raise Exception("Test adaptation failure")
    
    # 添加正常的适应规则
    normal_rule = AdaptationRule(
        event_type=SystemEvent.NETWORK_INTERFACE_CHANGED,
        condition=lambda state: True,  # 总是满足条件
        action=test_adaptation_action,
        cooldown_seconds=1,
        priority=1
    )
    
    # 添加会失败的适应规则
    failing_rule = AdaptationRule(
        event_type=SystemEvent.NETWORK_CONNECTIVITY_LOST,
        condition=lambda state: True,
        action=failing_adaptation_action,
        cooldown_seconds=1,
        priority=2
    )
    
    adaptability_manager.add_adaptation_rule(normal_rule)
    adaptability_manager.add_adaptation_rule(failing_rule)
    
    # 模拟网络接口变化
    print("  模拟网络接口变化...")
    with patch.object(adaptability_manager, '_interfaces_changed', return_value=True):
        adaptability_manager._detect_changes()
        adaptability_manager._apply_adaptation_rules()
    
    assert rule_triggered, "适应规则应该被触发"
    
    # 模拟网络连接丢失（会触发失败的规则）
    print("  模拟网络连接丢失...")
    adaptability_manager.current_state.internet_connectivity = False
    adaptability_manager.previous_state.internet_connectivity = True
    
    # 系统应该能够处理规则执行失败而不崩溃
    try:
        adaptability_manager._detect_changes()
        adaptability_manager._apply_adaptation_rules()
    except Exception as e:
        assert False, f"系统适应性管理器不应该因为规则失败而崩溃: {e}"
    
    # 验证统计信息
    stats = adaptability_manager.get_statistics()
    assert isinstance(stats, dict), "统计信息应该是字典"
    assert 'events_triggered' in stats, "统计信息应该包含事件触发数"
    assert 'rules_executed' in stats, "统计信息应该包含规则执行数"
    assert 'adaptations_successful' in stats, "统计信息应该包含成功适应数"
    assert 'adaptations_failed' in stats, "统计信息应该包含失败适应数"
    
    print(f"  统计信息: {stats}")
    
    # 应该有成功和失败的适应
    assert stats['rules_executed'] > 0, "应该有规则被执行"
    assert stats['adaptations_successful'] > 0, "应该有成功的适应"
    
    print("✅ 系统适应性测试通过")

def test_monitoring_stability():
    """测试监控稳定性"""
    print("\nTesting monitoring stability...")
    
    adaptability_manager = SystemAdaptabilityManager()
    
    # 启动监控
    print("  启动系统监控...")
    adaptability_manager.start_monitoring()
    
    # 等待几个监控周期
    time.sleep(2)
    
    # 验证监控正在运行
    assert adaptability_manager._monitoring_thread.is_alive(), "监控线程应该在运行"
    
    # 获取系统状态
    state = adaptability_manager.get_current_state()
    assert isinstance(state, SystemState), "应该返回SystemState对象"
    assert state.last_updated is not None, "应该有最后更新时间"
    
    print(f"  系统状态健康: {state.is_healthy()}")
    print(f"  网络接口数量: {len(state.network_interfaces)}")
    print(f"  互联网连通性: {state.internet_connectivity}")
    
    # 验证状态更新
    initial_update_time = state.last_updated
    time.sleep(1)
    
    updated_state = adaptability_manager.get_current_state()
    assert updated_state.last_updated > initial_update_time, "状态应该被更新"
    
    # 停止监控
    print("  停止系统监控...")
    adaptability_manager.stop_monitoring()
    
    # 验证监控已停止
    time.sleep(1)
    assert not adaptability_manager._monitoring_thread.is_alive(), "监控线程应该已停止"
    
    print("✅ 监控稳定性测试通过")

def test_concurrent_test_cancellation():
    """测试并发测试取消功能"""
    print("\nTesting concurrent test cancellation...")
    
    concurrent_tester = ConcurrentLatencyTester()
    
    # 创建节点
    nodes = []
    for i in range(15):
        node = Node(
            uuid=f"cancel-test-{i}",
            remark=f"cancel_node_{i}",
            protocol="vless",
            address="127.0.0.1",
            port=9000 + i
        )
        nodes.append(node)
    
    config = ConcurrentTestConfig(
        max_concurrent=3,
        timeout=2.0,  # 较长的超时时间
        strategy=TestStrategy.THREADING
    )
    
    # 在另一个线程中启动测试
    result_container = []
    exception_container = []
    
    def run_test():
        try:
            result = concurrent_tester.test_nodes_threaded(
                nodes=nodes,
                config=config
            )
            result_container.append(result)
        except Exception as e:
            exception_container.append(e)
    
    print("  启动并发测试...")
    test_thread = threading.Thread(target=run_test)
    test_thread.start()
    
    # 等待测试开始
    time.sleep(0.5)
    
    # 验证测试正在运行
    assert concurrent_tester.is_testing(), "测试应该正在运行"
    
    # 取消测试
    print("  取消测试...")
    concurrent_tester.cancel_test()
    
    # 等待测试线程完成
    test_thread.join(timeout=10)
    
    # 验证测试已完成且没有异常
    assert not test_thread.is_alive(), "测试线程应该已完成"
    assert len(exception_container) == 0, f"测试取消不应该产生异常: {exception_container}"
    
    # 验证测试不再运行
    assert not concurrent_tester.is_testing(), "测试应该已停止"
    
    print("✅ 并发测试取消功能测试通过")

def test_performance_statistics():
    """测试性能统计准确性"""
    print("\nTesting performance statistics accuracy...")
    
    concurrent_tester = ConcurrentLatencyTester()
    
    # 清除之前的统计
    concurrent_tester._total_tests_run = 0
    concurrent_tester._total_successful_tests = 0
    concurrent_tester._total_failed_tests = 0
    
    # 创建测试节点
    nodes = []
    for i in range(6):
        node = Node(
            uuid=f"stats-test-{i}",
            remark=f"stats_node_{i}",
            protocol="vless",
            address="127.0.0.1",
            port=7000 + i
        )
        nodes.append(node)
    
    config = ConcurrentTestConfig(
        max_concurrent=3,
        timeout=0.5,
        strategy=TestStrategy.THREADING
    )
    
    # 执行测试
    result = concurrent_tester.test_nodes_threaded(
        nodes=nodes,
        config=config
    )
    
    # 验证批量结果统计
    assert result.total_nodes == len(nodes), f"总节点数应该是{len(nodes)}"
    assert len(result.results) == len(nodes), f"结果数量应该是{len(nodes)}"
    assert result.completed_nodes >= 0, "完成节点数应该非负"
    assert result.completed_nodes <= len(nodes), "完成节点数不应该超过总数"
    
    print(f"  总节点数: {result.total_nodes}")
    print(f"  完成节点数: {result.completed_nodes}")
    print(f"  失败节点数: {result.failed_nodes}")
    print(f"  测试持续时间: {result.test_duration:.2f}s")
    
    # 验证全局统计
    stats = concurrent_tester.get_statistics()
    assert stats['total_tests_run'] == len(nodes), f"全局测试总数应该是{len(nodes)}"
    assert stats['total_successful_tests'] >= 0, "成功测试数应该非负"
    assert stats['total_failed_tests'] >= 0, "失败测试数应该非负"
    assert (stats['total_successful_tests'] + stats['total_failed_tests'] == 
            stats['total_tests_run']), "成功数+失败数应该等于总数"
    
    print(f"  全局统计: {stats}")
    
    # 验证成功率计算
    expected_success_rate = (
        stats['total_successful_tests'] / stats['total_tests_run'] * 100
        if stats['total_tests_run'] > 0 else 0
    )
    assert abs(stats['success_rate'] - expected_success_rate) < 0.01, "成功率计算应该准确"
    
    print("✅ 性能统计准确性测试通过")

if __name__ == "__main__":
    print("🧪 开始性能优化属性测试...")
    
    test_concurrent_processing_efficiency()
    test_async_vs_threading_strategies()
    test_system_adaptability()
    test_monitoring_stability()
    test_concurrent_test_cancellation()
    test_performance_statistics()
    
    print("\n🎉 所有性能优化属性测试都通过了！")