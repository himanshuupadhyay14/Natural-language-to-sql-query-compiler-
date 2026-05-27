from dataclasses import dataclass, field
import json
import re
from typing import List, Optional


with open("schema.json", encoding="utf-8") as schema_file:
    SCHEMA = json.load(schema_file)


TABLE_NAME = "students"
VALID_COLUMNS = set(SCHEMA.get(TABLE_NAME, []))


class CompileError(Exception):
    pass


@dataclass
class Condition:
    column: str
    operator: str
    value: object


@dataclass
class QueryAST:
    action: str
    table: str = TABLE_NAME
    aggregate: Optional[str] = None
    conditions: List[Condition] = field(default_factory=list)
    updates: List[Condition] = field(default_factory=list)
    insert_values: dict = field(default_factory=dict)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def tokenize(text: str) -> List[str]:
    cleaned = normalize_text(text.lower())
    return re.findall(r"[a-zA-Z']+|\d+", cleaned)


class Lexer:
    def analyze(self, text: str) -> List[str]:
        tokens = tokenize(text)
        if not tokens:
            raise CompileError("Please enter a query.")
        return tokens


class Parser:
    def parse(self, text: str, tokens: List[str]) -> QueryAST:
        action = self._detect_action(tokens)

        if action == "select":
            return self._parse_select(text)
        if action == "insert":
            return self._parse_insert(text)
        if action == "update":
            return self._parse_update(text)
        if action == "delete":
            return self._parse_delete(text)

        raise CompileError("Unsupported query type.")

    def _detect_action(self, tokens: List[str]) -> str:
        first = tokens[0]
        if first in {"show", "get", "find", "list", "display", "count", "average", "avg"}:
            return "select"
        if first in {"add", "insert", "create"}:
            return "insert"
        if first in {"update", "modify", "change"}:
            return "update"
        if first in {"delete", "remove"}:
            return "delete"
        return "select"

    def _parse_select(self, text: str) -> QueryAST:
        lowered = normalize_text(text.lower())
        aggregate = None
        if "count" in lowered:
            aggregate = "count"
        elif "average" in lowered or re.search(r"\bavg\b", lowered):
            aggregate = "avg"
        elif "sum" in lowered or "total" in lowered:
            aggregate = "sum"
        elif "maximum" in lowered or re.search(r"\bmax\b", lowered) or "highest" in lowered:
            aggregate = "max"
        elif "minimum" in lowered or re.search(r"\bmin\b", lowered) or "lowest" in lowered:
            aggregate = "min"

        return QueryAST(
            action="select",
            aggregate=aggregate,
            conditions=self._parse_conditions(text),
        )

    def _parse_insert(self, text: str) -> QueryAST:
        name = self._extract_phrase(text, r"\bname\s+(.+?)(?=\s+marks\b|\s+department\b|$)")
        marks = self._extract_number(text, r"\bmarks\s+(\d+)\b")
        department = self._extract_phrase(text, r"\bdepartment\s+(.+)$")

        if not (name and marks is not None and department):
            raise CompileError("Insert format should include name, marks, and department.")

        return QueryAST(
            action="insert",
            insert_values={
                "name": self._normalize_name(name),
                "marks": marks,
                "department": department.lower(),
            },
        )

    def _parse_update(self, text: str) -> QueryAST:
        source_text = text
        update_clauses = []

        new_name = self._extract_phrase(source_text, r"\bchange\s+name\s+to\s+(.+)$")
        if new_name:
            update_clauses.append(Condition("name", "=", self._normalize_name(new_name)))
            source_text = re.sub(r"\bchange\s+name\s+to\s+.+$", "", source_text, flags=re.IGNORECASE)

        new_department = self._extract_phrase(
            source_text,
            r"\b(?:change|set)\s+department\s+to\s+(.+)$",
        )
        if new_department:
            update_clauses.append(Condition("department", "=", new_department.lower()))
            source_text = re.sub(
                r"\b(?:change|set)\s+department\s+to\s+.+$",
                "",
                source_text,
                flags=re.IGNORECASE,
            )

        marks = self._extract_number(source_text, r"\bmarks\s+(\d+)\b")
        if marks is not None:
            update_clauses.append(Condition("marks", "=", marks))
            source_text = re.sub(r"\bmarks\s+\d+\b", "", source_text, flags=re.IGNORECASE)

        conditions = self._parse_conditions(source_text)

        if not conditions or not update_clauses:
            raise CompileError("Update format needs a target row and at least one new value.")

        return QueryAST(action="update", conditions=conditions, updates=update_clauses)

    def _parse_delete(self, text: str) -> QueryAST:
        conditions = self._parse_conditions(text)
        if not conditions:
            raise CompileError("Delete format needs at least one condition.")
        return QueryAST(action="delete", conditions=conditions)

    def _parse_conditions(self, text: str) -> List[Condition]:
        conditions = []

        student_id = self._extract_number(text, r"\bid\s+(\d+)\b")
        if student_id is not None:
            conditions.append(Condition("id", "=", student_id))

        name = self._extract_phrase(
            text,
            r"\b(?:name|named)\s+(.+?)(?=\s+(?:marks|department|id|greater|less|change|set)\b|$)",
        )
        if name:
            conditions.append(Condition("name", "=", self._normalize_name(name)))

        department = self._extract_phrase(
            text,
            r"\bdepartment\s+(.+?)(?=\s+(?:marks|name|id|greater|less|change|set)\b|$)",
        )
        if department:
            conditions.append(Condition("department", "=", department.lower()))

        greater_than = self._extract_number(text, r"\bgreater than\s+(\d+)\b")
        if greater_than is not None:
            conditions.append(Condition("marks", ">", greater_than))

        less_than = self._extract_number(text, r"\bless than\s+(\d+)\b")
        if less_than is not None:
            conditions.append(Condition("marks", "<", less_than))

        return conditions

    def _extract_phrase(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return None
        return normalize_text(match.group(1))

    def _extract_number(self, text: str, pattern: str) -> Optional[int]:
        match = re.search(pattern, text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _normalize_name(self, value: str) -> str:
        return " ".join(part.capitalize() for part in value.split())


class SemanticAnalyzer:
    def validate(self, ast: QueryAST) -> QueryAST:
        if ast.table != TABLE_NAME:
            raise CompileError("Only the students table is supported right now.")

        for condition in ast.conditions + ast.updates:
            if condition.column not in VALID_COLUMNS:
                raise CompileError(f"Unknown column: {condition.column}")

        for column in ast.insert_values:
            if column not in VALID_COLUMNS:
                raise CompileError(f"Unknown column: {column}")

        if "marks" in ast.insert_values and not isinstance(ast.insert_values["marks"], int):
            raise CompileError("Marks should be numeric.")

        for condition in ast.conditions + ast.updates:
            if condition.column == "marks" and not isinstance(condition.value, int):
                raise CompileError("Marks conditions should use numeric values.")

        return ast


class SQLGenerator:
    def generate(self, ast: QueryAST) -> dict:
        if ast.action == "select":
            return self._generate_select(ast)
        if ast.action == "insert":
            return self._generate_insert(ast)
        if ast.action == "update":
            return self._generate_update(ast)
        if ast.action == "delete":
            return self._generate_delete(ast)
        raise CompileError("Could not generate SQL for this request.")

    def _generate_select(self, ast: QueryAST) -> dict:
        select_part = "SELECT *"
        if ast.aggregate == "count":
            select_part = "SELECT COUNT(*)"
        elif ast.aggregate == "avg":
            select_part = "SELECT AVG(marks)"
        elif ast.aggregate == "sum":
            select_part = "SELECT SUM(marks)"
        elif ast.aggregate == "max":
            select_part = "SELECT MAX(marks)"
        elif ast.aggregate == "min":
            select_part = "SELECT MIN(marks)"

        where_sql, params = self._compile_conditions(ast.conditions)
        return {"sql": f"{select_part} FROM {ast.table}{where_sql};", "params": params}

    def _generate_insert(self, ast: QueryAST) -> dict:
        columns = list(ast.insert_values.keys())
        placeholders = ", ".join("?" for _ in columns)
        params = [ast.insert_values[column] for column in columns]
        return {
            "sql": f"INSERT INTO {ast.table} ({', '.join(columns)}) VALUES ({placeholders});",
            "params": params,
        }

    def _generate_update(self, ast: QueryAST) -> dict:
        set_sql = ", ".join(f"{item.column} = ?" for item in ast.updates)
        set_params = [item.value for item in ast.updates]
        where_sql, where_params = self._compile_conditions(ast.conditions)
        return {
            "sql": f"UPDATE {ast.table} SET {set_sql}{where_sql};",
            "params": set_params + where_params,
        }

    def _generate_delete(self, ast: QueryAST) -> dict:
        where_sql, params = self._compile_conditions(ast.conditions)
        return {"sql": f"DELETE FROM {ast.table}{where_sql};", "params": params}

    def _compile_conditions(self, conditions: List[Condition]) -> tuple[str, List[object]]:
        if not conditions:
            return "", []

        compiled = []
        params = []
        for condition in conditions:
            compiled.append(f"{condition.column} {condition.operator} ?")
            params.append(condition.value)
        return f" WHERE {' AND '.join(compiled)}", params


def compile_nl_query(text: str) -> dict:
    lexer = Lexer()
    parser = Parser()
    semantic_analyzer = SemanticAnalyzer()
    generator = SQLGenerator()

    tokens = lexer.analyze(text)
    ast = parser.parse(text, tokens)
    ast = semantic_analyzer.validate(ast)
    compiled = generator.generate(ast)
    compiled["tokens"] = tokens
    compiled["ast"] = ast
    return compiled
