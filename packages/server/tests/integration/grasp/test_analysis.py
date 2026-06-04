"""
Grasp 综合研判服务测试
"""

import pytest
import sys
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasp.analysis.analysis import (
    GraspAnalysisService, PlanAnalyzer, StepMerger, AnalysisReportGenerator,
    PlanApplicability, MergedPlan, AnalysisReport, TaskStep, StepConflict,
    ApplicabilityLevel, ConflictType,
)
from grasp.analysis.plans import Plan, PlanStore, PlanMatcher


@pytest.fixture
def sample_plan_store():
    """创建包含示例预案的 PlanStore"""
    store = PlanStore()

    # 城市地震搜救预案
    earthquake_plan = Plan(
        plan_id="plan-earthquake-001",
        title="城市地震搜救预案",
        description="针对城市区域发生6.0级以上地震后的紧急搜救预案",
        content="""{
            "id": "plan-earthquake-001",
            "disasterType": "地震",
            "disasterCategory": "自然灾害",
            "responseLevel": "Ⅰ级",
            "tasks": [
                {"taskId": "eq-001", "name": "生命搜救", "priority": "P0", "description": "网格化生命搜救", "assignedAgents": ["搜救队A"]},
                {"taskId": "eq-002", "name": "建筑结构安全评估", "priority": "P0", "description": "建筑安全快速评估", "assignedAgents": ["结构评估组"]},
                {"taskId": "eq-003", "name": "建立生命通道", "priority": "P0", "description": "清理主干道障碍物", "assignedAgents": ["工程抢险队"]},
                {"taskId": "eq-004", "name": "临时医疗点设立", "priority": "P1", "description": "设立临时医疗救治点", "assignedAgents": ["医疗救援组"]},
                {"taskId": "eq-005", "name": "受灾人员安置", "priority": "P1", "description": "设置临时避难所", "assignedAgents": ["后勤保障组"]}
            ]
        }""",
        tags=["地震", "搜救", "自然灾害"],
        applicable_scenarios=["城市地震", "建筑物倒塌"],
        status="ready",
    )
    store.add(earthquake_plan)

    # 危化品泄漏预案
    hazmat_plan = Plan(
        plan_id="plan-hazmat-001",
        title="危化品泄漏应急预案",
        description="针对危险化学品泄漏事故的应急响应预案",
        content="""{
            "id": "plan-hazmat-001",
            "disasterType": "危化品泄漏",
            "disasterCategory": "事故灾害",
            "responseLevel": "Ⅱ级",
            "tasks": [
                {"taskId": "hz-001", "name": "现场封锁", "priority": "P0", "description": "封锁泄漏区域", "assignedAgents": ["警戒组"]},
                {"taskId": "hz-002", "name": "泄漏源控制", "priority": "P0", "description": "控制泄漏源", "assignedAgents": ["处置组"]},
                {"taskId": "hz-003", "name": "人员疏散", "priority": "P0", "description": "疏散周边人员", "assignedAgents": ["疏散组"]},
                {"taskId": "hz-004", "name": "环境监测", "priority": "P1", "description": "持续监测环境指标", "assignedAgents": ["监测组"]},
                {"taskId": "hz-005", "name": "洗消处理", "priority": "P1", "description": "污染区域洗消", "assignedAgents": ["洗消组"]}
            ]
        }""",
        tags=["危化品", "泄漏", "事故灾害"],
        applicable_scenarios=["化学品泄漏", "工厂事故"],
        status="ready",
    )
    store.add(hazmat_plan)

    # 医疗救援预案
    medical_plan = Plan(
        plan_id="plan-medical-001",
        title="大规模伤亡医疗救援预案",
        description="针对大规模伤亡事件的医疗救援预案",
        content="""{
            "id": "plan-medical-001",
            "disasterType": "大规模伤亡",
            "disasterCategory": "公共卫生",
            "responseLevel": "Ⅰ级",
            "tasks": [
                {"taskId": "md-001", "name": "检伤分类", "priority": "P0", "description": "对伤员进行检伤分类", "assignedAgents": ["医疗组A"]},
                {"taskId": "md-002", "name": "临时医疗点设立", "priority": "P0", "description": "建立现场医疗点", "assignedAgents": ["医疗组B"]},
                {"taskId": "md-003", "name": "伤员转运", "priority": "P1", "description": "转运重伤员至医院", "assignedAgents": ["转运组"]},
                {"taskId": "md-004", "name": "心理干预", "priority": "P2", "description": "对受灾群众进行心理干预", "assignedAgents": ["心理干预组"]}
            ]
        }""",
        tags=["医疗", "救援", "公共卫生"],
        applicable_scenarios=["地震伤亡", "交通事故", "大规模伤亡"],
        status="ready",
    )
    store.add(medical_plan)

    return store


@pytest.fixture
def service(sample_plan_store):
    """创建综合研判服务"""
    matcher = PlanMatcher(sample_plan_store)
    return GraspAnalysisService(store=sample_plan_store, matcher=matcher)


class TestPlanAnalyzer:
    """预案适用性分析测试"""

    def test_analyze_applicability_earthquake(self, service):
        """测试地震场景适用性分析"""
        results = service.analyze_applicability(
            query="地震 搜救 城市",
            context={"disaster_type": "地震"},
            limit=5
        )

        assert len(results) > 0
        # 地震预案应该排在最前面
        assert results[0].plan.plan_id == "plan-earthquake-001"
        assert results[0].applicability_level == ApplicabilityLevel.HIGHLY_APPLICABLE

    def test_analyze_applicability_hazmat(self, service):
        """测试危化品场景适用性分析"""
        results = service.analyze_applicability(
            query="危化品 泄漏",
            context={"disaster_type": "危化品泄漏"},
            limit=5
        )

        assert len(results) > 0
        # 危化品预案应该排在最前面
        assert results[0].plan.plan_id == "plan-hazmat-001"

    def test_analyze_applicability_empty(self, service):
        """测试无匹配场景"""
        results = service.analyze_applicability(
            query="外星人入侵",
            limit=5
        )

        # 可能返回空或低匹配结果
        assert isinstance(results, list)

    def test_applicability_with_context(self, service):
        """测试带上下文的适用性分析"""
        results = service.analyze_applicability(
            query="地震",
            context={
                "disaster_type": "地震",
                "response_level": "Ⅰ级",
            },
            limit=5
        )

        # 带上下文应该提高匹配度
        assert len(results) > 0
        assert results[0].applicability_score > 0


class TestStepMerger:
    """步骤合并测试"""

    def test_merge_steps(self, service):
        """测试步骤合并"""
        applicabilities = service.analyze_applicability(
            query="地震 医疗",
            context={"disaster_type": "地震"},
            limit=5
        )

        merged = service.merge_steps(applicabilities)

        assert merged.merged_id.startswith("merged-")
        assert len(merged.merged_steps) > 0
        assert len(merged.source_plans) > 1  # 应该合并了多个预案

    def test_merge_steps_no_conflicts(self, service):
        """测试无冲突合并"""
        applicabilities = service.analyze_applicability(
            query="地震",
            limit=1
        )

        merged = service.merge_steps(applicabilities)

        # 单预案合并应该没有资源冲突
        # （除非同一Agent被分配到多个步骤）
        assert isinstance(merged, MergedPlan)

    def test_merge_deduplication(self, service):
        """测试步骤去重"""
        applicabilities = service.analyze_applicability(
            query="地震 医疗",
            context={"disaster_type": "地震"},
            limit=5
        )

        merged = service.merge_steps(applicabilities)

        # 检查是否有重复的步骤名
        step_names = [s.name for s in merged.merged_steps]
        assert len(step_names) == len(set(step_names)), "步骤名不应重复"


class TestAnalysisReportGenerator:
    """研判报告生成测试"""

    def test_generate_report(self, service):
        """测试报告生成"""
        applicabilities = service.analyze_applicability(
            query="地震 搜救",
            context={"disaster_type": "地震"},
            limit=5
        )

        merged = service.merge_steps(applicabilities)
        report = service.generate_report("地震 搜救", applicabilities, merged)

        assert report.report_id.startswith("report-")
        assert report.query == "地震 搜救"
        assert len(report.plan_applicabilities) > 0
        assert report.merged_plan is not None
        assert report.summary != ""
        assert len(report.recommendations) > 0
        assert len(report.risk_assessment) > 0

    def test_generate_report_no_match(self, service):
        """测试无匹配时的报告"""
        report = service.generate_report("外星人入侵", [], None)

        assert report.summary != ""
        assert len(report.recommendations) > 0


class TestGraspAnalysisService:
    """综合研判服务主入口测试"""

    def test_comprehensive_analysis(self, service):
        """测试综合研判分析"""
        result = service.comprehensive_analysis(
            query="城市地震 搜救 医疗",
            context={
                "disaster_type": "地震",
                "response_level": "Ⅰ级",
            },
            limit=5,
            generate_report=True,
        )

        assert result["status"] == "success"
        assert result["query"] == "城市地震 搜救 医疗"
        assert len(result["plan_applicabilities"]) > 0
        assert result["merged_plan"] is not None
        assert result["report"] is not None

    def test_comprehensive_analysis_no_match(self, service):
        """测试无匹配场景"""
        result = service.comprehensive_analysis(
            query="完全不相关的查询 xyz123",
            limit=5,
        )

        # 可能返回 no_match 或低匹配结果
        assert "status" in result

    def test_comprehensive_analysis_without_report(self, service):
        """测试不生成报告的研判"""
        result = service.comprehensive_analysis(
            query="地震",
            generate_report=False,
        )

        assert result["status"] == "success"
        assert result["report"] is None


class TestPlanApplicability:
    """预案适用性数据结构测试"""

    def test_to_dict(self):
        plan = Plan(
            plan_id="test-001",
            title="测试预案",
            description="测试",
            content="{}",
        )
        pa = PlanApplicability(
            plan=plan,
            applicability_level=ApplicabilityLevel.HIGHLY_APPLICABLE,
            applicability_score=0.85,
            applicable_tasks=[{"taskId": "t1", "name": "任务1"}],
            adaptation_notes="适用性良好",
        )

        d = pa.to_dict()
        assert d["applicability_level"] == "高度适用"
        assert d["applicability_score"] == 0.85
        assert len(d["applicable_tasks"]) == 1


class TestMergedPlan:
    """合并预案数据结构测试"""

    def test_to_dict(self):
        step = TaskStep(
            step_id="step-001",
            name="生命搜救",
            description="网格化生命搜救",
            priority="P0",
        )
        merged = MergedPlan(
            merged_id="merged-test",
            title="测试合并预案",
            description="测试",
            source_plans=["plan-001", "plan-002"],
            merged_steps=[step],
        )

        d = merged.to_dict()
        assert d["merged_id"] == "merged-test"
        assert len(d["merged_steps"]) == 1
        assert d["merged_steps"][0]["name"] == "生命搜救"
