"""Tests for safe SQLite execution and the graph-backed SQL Agent."""

import pytest

from app.agents.sql_agent import SqlAgent
from app.services.llm_service import GroqSqlService, build_sql_prompt, extract_sql
from app.tools import data_tools
from app.tools.sql_tools import DATASET_TABLE_NAME, execute_select_query, generate_query, validate_select_query


class FakeGroqSqlService:
    """Offline SQL generator used to keep unit tests independent of Groq."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def generate_sql(self, question: str, table_name: str, schema: dict[str, str]) -> str:
        self.calls.append((question, table_name, schema))
        return generate_query(question, list(schema))


def _sales_file(tmp_path, monkeypatch) -> str:
    file_id = "9" * 32
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / f"{file_id}.csv").write_bytes(
        b"Region,Category,Sales,Profit\nEast,Furniture,100,10\nWest,Technology,300,60\nEast,Technology,50,-5\n"
    )
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", uploads)
    return file_id


def _hr_file(tmp_path, monkeypatch) -> str:
    file_id = "7" * 32
    uploads = tmp_path / "uploads"
    uploads.mkdir(exist_ok=True)
    (uploads / f"{file_id}.csv").write_bytes(
        b"Age,Attrition,BusinessTravel,Department,EducationField,EmployeeNumber,MonthlyIncome,YearsAtCompany\n"
        b"30,Yes,Travel_Rarely,Sales,Life Sciences,1,5000,5\n"
        b"40,No,Travel_Frequently,HR,Medical,2,7000,10\n"
        b"20,Yes,Non-Travel,Sales,Technical Degree,3,4000,1\n"
        b"50,No,Travel_Rarely,HR,Medical,4,9000,20\n"
    )
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", uploads)
    return file_id


def _segment_file(tmp_path, monkeypatch) -> str:
    file_id = "5" * 32
    uploads = tmp_path / "uploads"
    uploads.mkdir(exist_ok=True)
    (uploads / f"{file_id}.csv").write_bytes(
        b"Segment,Profit\nConsumer,40\nCorporate,50\nConsumer,30\n"
    )
    monkeypatch.setattr(data_tools, "UPLOADS_DIRECTORY", uploads)
    return file_id


def test_sql_select_aggregation_and_group_by(tmp_path, monkeypatch) -> None:
    file_id = _sales_file(tmp_path, monkeypatch)
    columns, rows = execute_select_query(file_id, f'SELECT "Region", SUM("Profit") AS profit FROM "{DATASET_TABLE_NAME}" GROUP BY "Region" ORDER BY profit DESC')

    assert columns == ["Region", "profit"]
    assert rows == [{"Region": "West", "profit": 60} , {"Region": "East", "profit": 5}]


@pytest.mark.parametrize("sql", [
    "DELETE FROM sales",
    "DROP TABLE sales",
    "SELECT * FROM sales; DELETE FROM sales",
    "INSERT INTO sales VALUES (1)",
    "ALTER TABLE sales ADD COLUMN secret TEXT",
    "CREATE TABLE secret (value TEXT)",
    "ATTACH DATABASE 'other.db' AS other",
    "PRAGMA writable_schema = ON",
])
def test_sql_rejects_unsafe_statements(tmp_path, monkeypatch, sql) -> None:
    file_id = _sales_file(tmp_path, monkeypatch)

    with pytest.raises(ValueError):
        execute_select_query(file_id, sql)


@pytest.mark.parametrize("sql", [
    'SELECT "Attrition", COUNT(*) AS employee_count FROM "dataset" GROUP BY "Attrition"',
    'SELECT "Department", AVG("MonthlyIncome") FROM "dataset" GROUP BY "Department" ORDER BY 2 DESC LIMIT 1',
    'SELECT CASE WHEN "Attrition" = \'Yes\' THEN 1 ELSE 0 END AS attrition_flag FROM "dataset"',
])
def test_sql_validation_allows_read_only_analytical_queries(sql) -> None:
    assert validate_select_query(sql) == sql


@pytest.mark.parametrize(("response", "expected"), [
    ('SELECT "Attrition" FROM "dataset"', 'SELECT "Attrition" FROM "dataset"'),
    ('```sql\nSELECT "Attrition" FROM "dataset"\n```', 'SELECT "Attrition" FROM "dataset"'),
])
def test_extract_sql_handles_plain_and_fenced_llm_output(response, expected) -> None:
    assert extract_sql(response) == expected


def test_groq_prompt_requires_grouped_sum_for_highest_group_questions() -> None:
    prompt = build_sql_prompt(
        "Which segment has the highest profit?",
        DATASET_TABLE_NAME,
        {"Segment": "object", "Profit": "int64"},
    )

    assert "SUM()" in prompt
    assert "GROUP BY" in prompt
    assert "Do not order individual rows" in prompt
    assert '"Segment": "object"' in prompt
    assert "Which segment has the highest profit?" in prompt


def test_sql_agent_uses_groq_with_actual_schema_and_validates_result(tmp_path, monkeypatch) -> None:
    file_id = _hr_file(tmp_path, monkeypatch)

    class FakeGroqSqlService:
        def __init__(self) -> None:
            self.call = None

        def generate_sql(self, question, table_name, schema):
            self.call = (question, table_name, schema)
            return '```sql\nSELECT "Attrition", COUNT(*) AS employee_count FROM "dataset" GROUP BY "Attrition"\n```'

    def fail_if_real_groq_is_called(*_args, **_kwargs):
        raise AssertionError("Unit tests must not call the real Groq service.")

    monkeypatch.setattr(GroqSqlService, "generate_sql", fail_if_real_groq_is_called)
    service = FakeGroqSqlService()
    result = SqlAgent(llm_service=service).query(file_id, "How many employees are in each attrition category?")

    assert service.call == (
        "How many employees are in each attrition category?",
        DATASET_TABLE_NAME,
        {
            "Age": "int64", "Attrition": "object", "BusinessTravel": "object", "Department": "object",
            "EducationField": "object", "EmployeeNumber": "int64", "MonthlyIncome": "int64", "YearsAtCompany": "int64",
        },
    )
    assert result.rows == [{"Attrition": "No", "employee_count": 2}, {"Attrition": "Yes", "employee_count": 2}]


def test_sql_agent_rejects_unsafe_llm_sql(tmp_path, monkeypatch) -> None:
    file_id = _sales_file(tmp_path, monkeypatch)

    class UnsafeGroqSqlService:
        def generate_sql(self, *_args):
            return 'SELECT * FROM "dataset"; DROP TABLE "dataset"'

    with pytest.raises(ValueError, match="Only one SQL statement"):
        SqlAgent(llm_service=UnsafeGroqSqlService()).query(file_id, "Show all rows")


def test_sql_agent_generates_and_executes_natural_language_queries(tmp_path, monkeypatch) -> None:
    file_id = _sales_file(tmp_path, monkeypatch)
    service = FakeGroqSqlService()
    agent = SqlAgent(llm_service=service)

    region_result = agent.query(file_id, "Which region has the highest profit?")
    category_result = agent.query(file_id, "Show the top 5 categories by total sales.")

    assert region_result.rows == [{"region": "West", "total_profit": 60}]
    assert "GROUP BY" in region_result.sql
    assert category_result.rows[0] == {"category": "Technology", "total_sales": 350}
    assert "LIMIT 5" in category_result.sql
    assert len(service.calls) == 2


def test_sql_agent_aggregates_highest_group_questions_with_fake_llm(tmp_path, monkeypatch) -> None:
    sales_file_id = _sales_file(tmp_path, monkeypatch)
    segment_file_id = _segment_file(tmp_path, monkeypatch)
    hr_file_id = _hr_file(tmp_path, monkeypatch)
    service = FakeGroqSqlService()
    agent = SqlAgent(llm_service=service)

    highest_profit_by_region = agent.query(sales_file_id, "Which region has the highest profit?")
    highest_sales_by_category = agent.query(sales_file_id, "Which category has the highest sales?")
    highest_profit_by_segment = agent.query(segment_file_id, "Which segment has the highest profit?")
    attrition_counts = agent.query(hr_file_id, "How many employees are in each attrition category?")

    assert highest_profit_by_region.rows == [{"region": "West", "total_profit": 60}]
    assert highest_sales_by_category.rows == [{"category": "Technology", "total_sales": 350}]
    assert highest_profit_by_segment.rows == [{"segment": "Consumer", "total_profit": 70}]
    assert attrition_counts.rows == [{"Attrition": "No", "count": 2}, {"Attrition": "Yes", "count": 2}]
    for result in (highest_profit_by_region, highest_sales_by_category, highest_profit_by_segment):
        assert "SUM(" in result.sql
        assert "GROUP BY" in result.sql
        assert "ORDER BY" in result.sql
        assert result.sql.endswith("LIMIT 1")
    assert "COUNT(*)" in attrition_counts.sql
    assert "GROUP BY" in attrition_counts.sql
    assert len(service.calls) == 4


def test_sql_agent_generates_queries_from_hr_schema(tmp_path, monkeypatch) -> None:
    file_id = _hr_file(tmp_path, monkeypatch)
    service = FakeGroqSqlService()
    agent = SqlAgent(llm_service=service)

    attrition_counts = agent.query(file_id, "How many employees are in each attrition category?")
    average_age = agent.query(file_id, "What is the average age for each attrition category?")
    largest_department = agent.query(file_id, "Which department has the most employees?")
    average_income = agent.query(file_id, "What is the average monthly income by department?")
    average_tenure = agent.query(file_id, "What is the average years at company by business travel?")
    education_counts = agent.query(file_id, "How many employees are in each education field?")

    assert attrition_counts.rows == [{"Attrition": "No", "count": 2}, {"Attrition": "Yes", "count": 2}]
    assert average_age.rows == [{"Attrition": "No", "average_age": 45.0}, {"Attrition": "Yes", "average_age": 25.0}]
    assert largest_department.rows == [{"Department": "Sales", "count": 2}]
    assert average_income.rows == [{"Department": "HR", "average_monthly_income": 8000.0}, {"Department": "Sales", "average_monthly_income": 4500.0}]
    assert '"MonthlyIncome"' in average_income.sql
    assert 'AVG("YearsAtCompany")' in average_tenure.sql
    assert 'GROUP BY "BusinessTravel"' in average_tenure.sql
    assert education_counts.rows == [
        {"EducationField": "Life Sciences", "count": 1},
        {"EducationField": "Medical", "count": 2},
        {"EducationField": "Technical Degree", "count": 1},
    ]
    assert f'FROM "{DATASET_TABLE_NAME}"' in attrition_counts.sql
    assert len(service.calls) == 6
