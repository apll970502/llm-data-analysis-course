# import sys
# from pathlib import Path


# def get_project_root(start_dir=None):
#     """start_dir에서 위로 올라가며 data 폴더를 가진 폴더를 찾아 반환한다.

#     start_dir을 생략하면 현재 폴더에서 탐색을 시작한다.
#     """

#     # if start_dir is None:
#     #     start_dir = Path.cwd()

#     # start = Path(start_dir).resolve()
#     # current = start
#     # project_root = None
#     current = Path.cwd().parent

#     while True:
#         # 만약 data 폴더가 있다면 현재 폴더를 프로젝트 루트로 결정하고 탐색을 종료한다.
#         if (current / "data").is_dir():
#             project_root = current
#             break

#         # 더 이상 위로 올라갈 수 없는데도 찾지 못했다면 오류를 발생시킨다.
#         # if current.parent == current:
#         #     raise FileNotFoundError(
#         #         f"data 폴더를 찾지 못했습니다. (탐색 시작: {})"
#         #     )

#         # data 폴더가 없다면 부모 폴더로 한 단계 올라간다.
#         current = current.parent

#     return project_root


# def get_data_dir(start_dir=None):
#     """프로젝트 루트 아래의 data 폴더 경로를 반환한다."""
#     return get_project_root(start_dir) / "data"


from pathlib import Path


def get_project_root():
    current = Path(__file__).resolve().parent

    while current != current.parent:
        if (current / "data").is_dir():
            return current

        current = current.parent

    raise FileNotFoundError("프로젝트 루트를 찾을 수 없습니다.")


def get_data_dir():
    return get_project_root() / "data"