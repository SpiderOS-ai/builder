/* eslint-disable i18next/no-literal-string */
import { useEffect, useState } from "react";

interface UserInfo {
  id: string | null;
  email: string | null;
  name: string | null;
}

function getInitials(email: string | null, name: string | null): string {
  if (name) {
    return name
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }
  if (email) {
    return email[0].toUpperCase();
  }
  return "?";
}

export function Navbar() {
  const [user, setUser] = useState<UserInfo | null>(null);

  useEffect(() => {
    fetch("/api/user/info")
      .then((r) => r.json())
      .then((data: UserInfo) => setUser(data))
      .catch(() => {});
  }, []);

  function handleLogout() {
    window.location.href = "/logout";
  }

  return (
    <nav className="spideros-navbar">
      <div className="spideros-navbar__left">
        <a href="https://spideros.dev" className="spideros-navbar__back">
          ← SpiderOS
        </a>
        <div className="spideros-navbar__brand">Builder</div>
      </div>
      <div className="spideros-navbar__right">
        {user?.email && (
          <div className="spideros-navbar__user">
            <div className="spideros-navbar__avatar">
              {getInitials(user.email, user.name)}
            </div>
            <span>{user.email}</span>
          </div>
        )}
        <button
          className="spideros-navbar__logout"
          onClick={handleLogout}
          type="button"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}
