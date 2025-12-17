from __future__ import annotations

import os
from typing import Set
from dotenv import load_dotenv

load_dotenv()


class UserWhitelist:
    """허용된 사용자 이메일 관리"""

    def __init__(self):
        self.allowed_emails: Set[str] = set()
        self._load_whitelist()

    def _load_whitelist(self) -> None:
        """환경 변수 또는 파일에서 화이트리스트 로드"""
        # 방법 1: 환경 변수에서 로드
        env_emails = os.getenv("ALLOWED_EMAILS", "")
        if env_emails:
            self.allowed_emails.update(
                email.strip().lower() for email in env_emails.split(",") if email.strip()
            )

        # 방법 2: 파일에서 로드
        whitelist_file = os.getenv("WHITELIST_FILE")
        if whitelist_file and os.path.exists(whitelist_file):
            with open(whitelist_file, "r") as f:
                file_emails = [line.strip().lower() for line in f if line.strip() and not line.startswith("#")]
                self.allowed_emails.update(file_emails)

    def is_allowed(self, email: str) -> bool:
        """이메일이 화이트리스트에 있는지 확인"""
        return email.lower() in self.allowed_emails

    def add_email(self, email: str) -> bool:
        """이메일을 화이트리스트에 추가"""
        email_lower = email.lower()
        if email_lower not in self.allowed_emails:
            self.allowed_emails.add(email_lower)
            self._save_to_file()
            return True
        return False

    def remove_email(self, email: str) -> bool:
        """이메일을 화이트리스트에서 제거"""
        email_lower = email.lower()
        if email_lower in self.allowed_emails:
            self.allowed_emails.discard(email_lower)
            self._save_to_file()
            return True
        return False

    def _save_to_file(self) -> None:
        """화이트리스트를 파일에 저장"""
        whitelist_file = os.getenv("WHITELIST_FILE")
        if whitelist_file:
            with open(whitelist_file, "w") as f:
                f.write("\n".join(sorted(self.allowed_emails)))


# 싱글톤 인스턴스
whitelist = UserWhitelist()
