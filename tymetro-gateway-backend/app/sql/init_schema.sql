-- ------------------------------------------------------------
-- Database Initial SQL Script for tymetro-gateway (SQLite / General SQL)
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- 1. Table structure for users
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `org_id` INTEGER NOT NULL,
  `org_code` VARCHAR(50) DEFAULT NULL,
  `account` VARCHAR(50) NOT NULL UNIQUE,
  `user_name` VARCHAR(100) DEFAULT NULL,
  `password` VARCHAR(255) DEFAULT NULL,
  `enable_at` DATETIME DEFAULT NULL,
  `disable_at` DATETIME DEFAULT NULL,
  `lastModify_at` DATETIME DEFAULT NULL,
  `lastLogin_at` DATETIME DEFAULT NULL,
  `refresh_token` VARCHAR(500) DEFAULT NULL,
  `refresh_token_expiry_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `is_mobile` BOOLEAN NOT NULL DEFAULT 0,
  `is_active` BOOLEAN NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_by` INTEGER NOT NULL DEFAULT 0,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_by` INTEGER NOT NULL DEFAULT 0
);

-- ------------------------------------------------------------
-- 2. Initial Mock Data for users (Default Admin User)
-- 帳號: admin | 密碼: admin123 (已預先 Bcrypt 加密)
-- ------------------------------------------------------------
INSERT INTO `users` (
  `org_id`, `org_code`, `account`, `user_name`, `password`, `enable_at`, `is_mobile`, `is_active`, `created_by`, `updated_by`
) VALUES (
  1, 'HQ', 'admin', '系統管理員', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', CURRENT_TIMESTAMP, 0, 1, 0, 0
);
