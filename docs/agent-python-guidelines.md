아래 내용을 그대로 `AGENTS.md`, `CLAUDE.md`, 또는 `docs/agent-python-guidelines.md` 등에 넣어 사용하시면 됩니다.

````markdown
# Python Agent Work Guidelines

이 문서는 에이전트가 Python 프로젝트를 수정할 때 반드시 참고해야 하는 작업 규칙이다.<br>
목표는 코드 품질을 높이는 것뿐 아니라, **런타임 오류를 사전에 줄이고**, 에이전트가 추측에 의존하지 않도록 프로젝트 구조와 검증 절차를 명확히 하는 것이다.

---

## 1. 타입 힌트는 가능한 한 구체적으로 작성한다

새로 추가하거나 수정하는 모든 함수에는 인자 타입과 반환 타입을 명시한다.

나쁜 예:

```python
def load_config(path):
    ...
````

좋은 예:

```python
from pathlib import Path

def load_config(path: Path) -> dict[str, str]:
    ...
```

너무 느슨한 타입도 피한다.

나쁜 예:

```python
def process(data: dict) -> list:
    ...
```

좋은 예:

```python
def process(data: dict[str, int]) -> list[int]:
    ...
```

입력값을 변경하지 않는 함수라면 `list`, `dict`보다 더 추상적인 타입을 우선 고려한다.

```python
from collections.abc import Mapping, Sequence

def summarize(items: Sequence[str]) -> str:
    ...

def normalize(config: Mapping[str, str]) -> dict[str, str]:
    ...
```

기본 원칙:

* 모든 public 함수에는 명시적인 타입을 작성한다.
* 반환값이 없으면 `-> None`을 명시한다.
* 경로는 문자열보다 `pathlib.Path`를 우선 사용한다.
* `dict`, `list`, `tuple`은 가능한 한 내부 타입까지 명시한다.
* 함수 시그니처만 보고 입력과 출력의 의미를 이해할 수 있어야 한다.

---

## 2. 정적 타입 검사를 반드시 통과시킨다

타입 힌트만 작성하고 검사하지 않으면 효과가 제한적이다.
코드 수정 후에는 반드시 정적 타입 검사를 실행한다.

권장 도구:

* `mypy`
* `pyright`
* `basedpyright`

예시 명령:

```bash
mypy src
```

또는:

```bash
pyright
```

`mypy` 사용 시 권장 설정 예시:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
no_implicit_optional = true
```

특히 다음 옵션은 중요하다.

```toml
disallow_untyped_defs = true
disallow_incomplete_defs = true
```

이 옵션들은 타입 없는 함수를 새로 추가하는 것을 방지한다.

작업 규칙:

* 타입 검사 실패 상태로 작업을 완료하지 않는다.
* 타입 오류를 무시하기 위해 무리하게 `Any`, `cast`, `type: ignore`를 사용하지 않는다.
* `type: ignore`를 사용할 경우 반드시 이유를 주석으로 남긴다.

---

## 3. `Any` 사용을 강하게 제한한다

`Any`는 타입 검사를 사실상 우회한다.
에이전트는 복잡한 타입을 만났을 때 `Any`로 회피하지 말아야 한다.

피해야 할 예:

```python
from typing import Any

def handle(payload: Any) -> Any:
    ...
```

가능하면 구조를 명시한다.

```python
from typing import TypedDict

class UserPayload(TypedDict):
    id: int
    name: str
    email: str | None

def handle(payload: UserPayload) -> str:
    ...
```

`Any`를 사용할 수 있는 경우:

* 외부 라이브러리의 타입 정보가 없고, 타입을 좁히기 어렵다.
* 점진적 마이그레이션 중이라 임시로 필요하다.
* 런타임에서 실제 타입을 검증한 뒤 내부 타입으로 변환한다.

단, 이 경우에도 주석으로 이유를 남긴다.

```python
from typing import Any

def parse_vendor_payload(payload: Any) -> VendorPayload:
    # External vendor SDK does not provide type information.
    # Validate and convert to internal model immediately.
    ...
```

기본 원칙:

* `Any`는 마지막 수단이다.
* `Any`를 받은 값은 가능한 한 빠르게 검증된 내부 타입으로 변환한다.
* 함수 전체의 입력과 출력을 `Any`로 두지 않는다.

---

## 4. 외부 입력에는 런타임 검증을 추가한다

Python 타입 힌트는 실행 시 자동으로 강제되지 않는다.
따라서 외부에서 들어오는 값은 별도의 런타임 검증이 필요하다.

검증이 필요한 대표 영역:

* 환경 변수
* CLI 인자
* JSON/YAML 설정 파일
* HTTP 요청/응답
* DB에서 읽은 데이터
* LLM 응답
* 사용자 입력
* 외부 API 응답

위험한 예:

```python
import os

api_key = os.environ["API_KEY"]
timeout = int(os.environ["TIMEOUT"])
```

더 나은 방식:

```python
from pydantic import BaseModel, Field

class Settings(BaseModel):
    api_key: str
    timeout: int = Field(default=30, gt=0)
```

외부 입력 검증에는 다음 방식을 우선 고려한다.

* `Pydantic` 모델
* 명시적인 검증 함수
* `TypedDict` + 수동 검증
* `dataclass` + 별도 검증 로직

기본 원칙:

* 외부 데이터는 신뢰하지 않는다.
* 외부 데이터는 프로젝트 내부 모델로 변환한 뒤 사용한다.
* 검증되지 않은 `dict`를 비즈니스 로직 깊숙이 전달하지 않는다.
* LLM 응답도 외부 입력으로 보고 검증한다.

---

## 5. 테스트는 에이전트가 실행 가능한 명령으로 고정한다

테스트가 있어도 실행 방법이 불명확하면 에이전트가 제대로 검증할 수 없다.
프로젝트에는 명확한 테스트 명령이 있어야 한다.

예시:

```bash
pytest
```

또는:

```bash
make test
```

가능하면 전체 검증 명령을 하나로 통합한다.

```bash
make check
```

예시 `Makefile`:

```makefile
test:
	pytest

typecheck:
	mypy src

lint:
	ruff check .

format-check:
	ruff format --check .

check:
	ruff check .
	ruff format --check .
	mypy src
	pytest
```

에이전트 작업 규칙:

* 동작을 변경했다면 테스트를 추가하거나 수정한다.
* 작업 완료 전 전체 테스트를 실행한다.
* 테스트 실패를 무시하지 않는다.
* 실패한 테스트를 삭제하거나 약화해서 통과시키지 않는다.
* 테스트가 실패하면 원인을 분석하고 코드 또는 테스트를 정정한다.

---

## 6. Ruff로 린트와 포맷을 통합한다

Python 프로젝트에서는 `ruff`를 사용해 린트와 포맷을 통합한다.

기본 명령:

```bash
ruff check .
ruff format .
```

검증용 명령:

```bash
ruff check .
ruff format --check .
```

권장 설정 예시:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",
    "F",
    "I",
    "B",
    "UP",
    "SIM",
    "ANN",
]
ignore = []
```

주요 규칙 의미:

* `E`, `F`: 기본 오류 및 스타일 검사
* `I`: import 정렬
* `B`: 버그 가능성 검사
* `UP`: 최신 Python 문법 권장
* `SIM`: 단순화 가능한 코드 검사
* `ANN`: 타입 어노테이션 검사

기본 원칙:

* 포맷은 수동 취향보다 도구에 맡긴다.
* import 정렬도 도구에 맡긴다.
* 새 코드에는 린트 오류를 남기지 않는다.
* 기존 코드의 대규모 포맷 변경은 별도 작업으로 분리한다.

---

## 7. 함수는 작게 만들고, 부작용은 밖으로 분리한다

에이전트는 큰 함수와 복잡한 부작용이 섞인 코드를 수정할 때 실수하기 쉽다.
함수는 작고 목적이 분명해야 한다.

피해야 할 구조:

```python
def run():
    # 환경 변수 읽기
    # 파일 읽기
    # 데이터 파싱
    # API 호출
    # DB 저장
    # 출력
    ...
```

권장 구조:

```python
from pathlib import Path

def load_input(path: Path) -> str:
    ...

def parse_input(raw: str) -> list[Item]:
    ...

def process_items(items: list[Item]) -> Result:
    ...

def save_result(result: Result, path: Path) -> None:
    ...
```

특히 다음을 분리한다.

* 순수 계산 로직
* 파일 입출력
* 네트워크 요청
* 데이터베이스 접근
* CLI 출력
* 환경 변수 로딩

기본 원칙:

* 핵심 비즈니스 로직은 가능한 한 순수 함수로 작성한다.
* 파일, DB, 네트워크 접근은 바깥 계층으로 분리한다.
* 함수 하나는 하나의 책임만 가진다.
* 테스트 가능한 단위로 코드를 나눈다.
* 복잡한 함수는 수정 전에 먼저 분리할 수 있는지 검토한다.

---

## 8. 예외 처리는 구체적으로 작성한다

넓은 예외 처리는 오류를 숨긴다.
특히 `except Exception: pass`는 원칙적으로 금지한다.

피해야 할 예:

```python
try:
    ...
except Exception:
    pass
```

더 나은 예:

```python
try:
    config = load_config(path)
except FileNotFoundError as exc:
    raise RuntimeError(f"Config file not found: {path}") from exc
except ValueError as exc:
    raise RuntimeError(f"Invalid config file: {path}") from exc
```

예외 처리 원칙:

* 어떤 예외를 잡는지 명확히 한다.
* 예외를 잡는 이유가 분명해야 한다.
* 오류를 조용히 무시하지 않는다.
* 재발생시킬 때는 원래 예외를 보존한다.
* `raise ... from exc`를 사용해 원인 추적을 유지한다.

허용 가능한 넓은 예외 처리 예:

```python
try:
    run_job()
except Exception as exc:
    logger.exception("Job failed")
    raise
```

이 경우에도 예외를 숨기지 않고 로깅 후 다시 발생시킨다.

기본 원칙:

* broad exception은 원칙적으로 피한다.
* 오류 메시지에는 문제 상황을 이해할 수 있는 맥락을 포함한다.
* 실패를 정상 흐름처럼 감추지 않는다.

---

## 9. 데이터 구조는 `dict` 남발보다 모델화한다

중첩된 `dict`는 에이전트가 구조를 잘못 이해하기 쉽고, 런타임 오류도 자주 만든다.

피해야 할 예:

```python
user = {
    "id": 1,
    "profile": {
        "name": "Kim",
        "age": 30,
    },
}
```

내부 데이터는 `dataclass`를 우선 고려한다.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Profile:
    name: str
    age: int

@dataclass(frozen=True)
class User:
    id: int
    profile: Profile
```

외부 입력 검증이 필요하면 `Pydantic` 모델을 우선 고려한다.

```python
from pydantic import BaseModel

class Profile(BaseModel):
    name: str
    age: int

class User(BaseModel):
    id: int
    profile: Profile
```

선택 기준:

* 내부 계산용 데이터: `dataclass`
* 외부 입력 검증: `Pydantic`
* 간단한 고정 구조: `TypedDict`
* 불변 값 묶음: `dataclass(frozen=True)`

기본 원칙:

* 의미 있는 데이터 구조에는 이름을 붙인다.
* 깊게 중첩된 `dict`를 여러 계층에 전달하지 않는다.
* 데이터 구조 변경 시 타입 또는 모델을 함께 수정한다.
* 문자열 키 오타로 인한 런타임 오류를 줄인다.

---

## 10. `None` 가능성을 명확히 처리한다

`NoneType` 오류는 Python에서 매우 흔한 런타임 오류다.
값이 없을 수 있다면 타입에 반드시 반영한다.

잘못된 예:

```python
def find_user(user_id: int) -> User:
    ...
```

실제로 사용자를 찾지 못할 수 있다면 다음처럼 작성한다.

```python
def find_user(user_id: int) -> User | None:
    ...
```

사용하는 쪽에서는 반드시 `None`을 처리한다.

```python
user = find_user(1)

if user is None:
    raise ValueError("User not found")

print(user.name)
```

피해야 할 방식:

```python
user = find_user(1)
print(user.name)  # user가 None이면 런타임 오류 발생
```

기본 원칙:

* 없을 수 있는 값은 `T | None`으로 표시한다.
* `None` 체크 없이 속성이나 메서드에 접근하지 않는다.
* `Optional` 값을 반환하는 함수는 호출부에서 반드시 처리한다.
* `None`을 오류로 볼지, 정상적인 부재 상태로 볼지 명확히 한다.
* 불필요한 `None` 반환보다 명확한 예외가 더 적합한 경우도 있다.

---

## Required Verification

코드 수정 후 가능한 경우 다음 검증 명령을 실행한다.

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

프로젝트에 통합 명령이 있다면 그것을 우선 사용한다.

```bash
make check
```

또는:

```bash
just check
```

---

## General Agent Rules

에이전트는 Python 코드를 수정할 때 다음 원칙을 따른다.

1. 새 함수와 수정한 함수에는 명시적인 타입 힌트를 작성한다.
2. `Any` 사용은 피한다. 불가피하면 이유를 주석으로 남긴다.
3. 외부 입력은 검증한 뒤 내부 모델로 변환한다.
4. 파일 경로는 가능하면 `pathlib.Path`를 사용한다.
5. 비즈니스 로직과 I/O를 분리한다.
6. 넓은 예외 처리는 피한다.
7. `None` 가능성은 타입과 코드에서 명확히 처리한다.
8. 동작 변경 시 테스트를 추가하거나 수정한다.
9. 작업 후 린트, 포맷 검사, 타입 검사, 테스트를 실행한다.
10. 검증 실패를 무시하지 않고 원인을 수정한다.

```

핵심적으로는 `AGENTS.md`에 넣는 것이 가장 적합합니다. Codex, Claude Code, 기타 에이전트가 모두 참고하기 쉽게 하려면 파일명을 `AGENTS.md`로 두고, 프로젝트별 세부 명령만 마지막의 `Required Verification` 부분에 맞게 수정하시면 됩니다.
```
