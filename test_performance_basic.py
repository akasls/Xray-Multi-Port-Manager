#!/usr/bin/env python3
"""
基础性能测试
"""
import time
import threading
from xray_gui.core.concurrent_latency_tester import (
    ConcurrentLatencyTester, 
    ConcurrentTestConfig, 
    TestStrategy,
    BatchTestResult
)
from xray_gui.core.node import Node

def test_basic_concurrent_functionality():
    """测试基本并发功能"""
    print("Testing basic concurrent functionality...")
    
    concurrent_tester = ConcurrentLatencyTester()
    
    # 创建少量测试节点
    nodes = []
    for i in range(3):
        node = Node(
            uuid=f"test-{i}",
            remark=f"node_{i}",
            protocol="vless",
            address="127.0.0.1",
            port=8000 + i
        )
        nodes.append(node)
    
    config = ConcurrentTestConfig(
        max_concurrent=2,
        timeout=0.5,
        strategy=TestStrategy.THREADING
    )
    
    print(f"  Testing {len(nodes)} nodes...")
    
    start_time = time.time()
    result = concurrent_tester.test_nodes_threaded(nodes=nodes, config=config)
    duration = time.time() - start_time
    
    print(f"  Test completed in {duration:.2f}s")
    print(f"  Results: {len(result.results)} nodes tested")
    
    # 基本验证
    assert isinstance(result, BatchTestResult), "Should return BatchTestResult"
    assert len(result.results) == len(nodes), "Should test all nodes"
    assert result.total_nodes == len(nodes), "Total nodes should match"
    
    # 验证每个结果都有基本信息
    for test_result in result.results:
        assert test_result.node_uuid is not None, "Should have node UUID"
        assert test_result.timestamp is not None, "Should have timestamp"
        assert test_result.latency is not None, "Should have latency result"
    
    print("✅ Basic concurrent functionality test passed")

def test_concurrent_vs_serial_efficiency():
    """测试并发与串行的效率对比"""
    print("\nTesting concurrent vs serial efficiency...")
    
    concurrent_tester = ConcurrentLatencyTester()
    
    # 创建测试节点
    nodes = []
    for i in range(4):
        node = Node(
            uuid=f"efficiency-test-{i}",
            remark=f"efficiency_node_{i}",
            protocol="vless",
            address="127.0.0.1",
            port=9000 + i
        )
        nodes.append(node)
    
    timeout = 0.3
    
    # 并发测试
    config = ConcurrentTestConfig(
        max_concurrent=4,
        timeout=timeout,
        strategy=TestStrategy.THREADING
    )
    
    start_time = time.time()
    concurrent_result = concurrent_tester.test_nodes_threaded(nodes=nodes, config=config)
    concurrent_duration = time.time() - start_time
    
    # 串行测试（max_concurrent=1）
    serial_config = ConcurrentTestConfig(
        max_concurrent=1,
        timeout=timeout,
        strategy=TestStrategy.THREADING
    )
    
    start_time = time.time()
    serial_result = concurrent_tester.test_nodes_threaded(nodes=nodes, config=serial_config)
    serial_duration = time.time() - start_time
    
    print(f"  Concurrent duration: {concurrent_duration:.2f}s")
    print(f"  Serial duration: {serial_duration:.2f}s")
    
    # 验证结果
    assert len(concurrent_result.results) == len(nodes), "Concurrent should test all nodes"
    assert len(serial_result.results) == len(nodes), "Serial should test all nodes"
    
    # 并发应该比串行快（至少不会更慢）
    efficiency_ratio = serial_duration / concurrent_duration if concurrent_duration > 0 else 1
    print(f"  Efficiency ratio: {efficiency_ratio:.2f}x")
    
    # 在测试环境中，并发至少应该不比串行慢
    assert efficiency_ratio >= 0.8, f"Concurrent should not be much slower than serial: {efficiency_ratio:.2f}x"
    
    print("✅ Concurrent vs serial efficiency test passed")

def test_cancellation_functionality():
    """测试取消功能"""
    print("\nTesting cancellation functionality...")
    
    concurrent_tester = ConcurrentLatencyTester()
    
    # 创建节点
    nodes = []
    for i in range(5):
        node = Node(
            uuid=f"cancel-test-{i}",
            remark=f"cancel_node_{i}",
            protocol="vless",
            address="127.0.0.1",
            port=10000 + i
        )
        nodes.append(node)
    
    config = ConcurrentTestConfig(
        max_concurrent=2,
        timeout=1.0,
        strategy=TestStrategy.THREADING
    )
    
    # 在线程中启动测试
    result_container = []
    
    def run_test():
        result = concurrent_tester.test_nodes_threaded(nodes=nodes, config=config)
        result_container.append(result)
    
    test_thread = threading.Thread(target=run_test)
    test_thread.start()
    
    # 等待测试开始
    time.sleep(0.2)
    
    # 验证测试正在运行
    is_testing_before = concurrent_tester.is_testing()
    print(f"  Test running: {is_testing_before}")
    
    # 取消测试
    concurrent_tester.cancel_test()
    print("  Test cancelled")
    
    # 等待测试完成
    test_thread.join(timeout=5)
    
    # 验证测试已停止
    is_testing_after = concurrent_tester.is_testing()
    print(f"  Test running after cancel: {is_testing_after}")
    
    assert not test_thread.is_alive(), "Test thread should complete"
    assert not is_testing_after, "Test should not be running after cancel"
    
    print("✅ Cancellation functionality test passed")

def test_statistics_tracking():
    """测试统计信息跟踪"""
    print("\nTesting statistics tracking...")
    
    concurrent_tester = ConcurrentLatencyTester()
    
    # 重置统计
    concurrent_tester._total_tests_run = 0
    concurrent_tester._total_successful_tests = 0
    concurrent_tester._total_failed_tests = 0
    
    # 创建节点
    nodes = []
    for i in range(3):
        node = Node(
            uuid=f"stats-test-{i}",
            remark=f"stats_node_{i}",
            protocol="vless",
            address="127.0.0.1",
            port=11000 + i
        )
        nodes.append(node)
    
    config = ConcurrentTestConfig(
        max_concurrent=2,
        timeout=0.3,
        strategy=TestStrategy.THREADING
    )
    
    # 执行测试
    result = concurrent_tester.test_nodes_threaded(nodes=nodes, config=config)
    
    # 验证统计信息
    stats = concurrent_tester.get_statistics()
    
    print(f"  Statistics: {stats}")
    
    assert stats['total_tests_run'] == len(nodes), f"Should run {len(nodes)} tests"
    assert stats['total_successful_tests'] >= 0, "Successful tests should be non-negative"
    assert stats['total_failed_tests'] >= 0, "Failed tests should be non-negative"
    assert (stats['total_successful_tests'] + stats['total_failed_tests'] == 
            stats['total_tests_run']), "Success + Failed should equal Total"
    
    # 验证批量结果统计
    result.update_statistics()
    assert result.total_nodes == len(nodes), "Batch result should track total nodes"
    assert result.completed_nodes >= 0, "Completed nodes should be non-negative"
    
    print("✅ Statistics tracking test passed")

if __name__ == "__main__":
    print("🧪 Starting basic performance tests...")
    
    try:
        test_basic_concurrent_functionality()
        test_concurrent_vs_serial_efficiency()
        test_cancellation_functionality()
        test_statistics_tracking()
        
        print("\n🎉 All basic performance tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()