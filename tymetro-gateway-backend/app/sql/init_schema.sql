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

-- ------------------------------------------------------------
-- 3. Table structure for cars
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `cars` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,                 -- 流水序
  `train_code` VARCHAR(20) NOT NULL,                      -- 車組編號 (如 AC-105)
  `car_no` INTEGER NOT NULL,                               -- 車廂序號 (1, 2, 3, 4)
  `car_vin` VARCHAR(50) DEFAULT NULL UNIQUE,              -- 車廂唯一識別碼/車號
  `car_type` VARCHAR(20) DEFAULT NULL,                    -- 車廂類型 (EXPRESS, COMMUTER)
  `car_tag` VARCHAR(20) DEFAULT NULL,                     -- 車廂標籤
  `car_status` VARCHAR(20) DEFAULT NULL,                  -- 狀態 (OPERATING, MAINTENANCE, IDLE, OFFLINE, ABNORMAL)
  `is_active` BOOLEAN NOT NULL DEFAULT 1,                  -- 是否合法/啟用
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,-- 建立日期
  `created_by` INTEGER NOT NULL DEFAULT 0,                 -- 建立人員Seq
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,-- 異動日期
  `updated_by` INTEGER NOT NULL DEFAULT 0,                 -- 異動人員Seq
  `last_seen_at` DATETIME DEFAULT NULL                     -- 最後通訊時間
);

INSERT INTO `cars` (
  `id`, `train_code`, `car_no`, `car_vin`, `car_type`, `car_tag`, `car_status`,
  `is_active`, `created_at`, `created_by`, `updated_at`, `updated_by`, `last_seen_at`
) VALUES
(1, '101', 1, '1101', 'COMMUTER', NULL, 'OPERATING', 1, '2026-05-02 08:44:07', 0, '2026-07-23 14:53:33.226095', 0, '2026-07-23 14:53:33.108141'),
(2, '101', 2, '1201', 'COMMUTER', NULL, 'OPERATING', 1, '2026-05-02 08:44:49', 0, '2026-07-23 14:53:33.226095', 0, '2026-07-23 14:53:33.05317'),
(3, '101', 3, '1301', 'COMMUTER', NULL, 'OPERATING', 1, '2026-05-02 08:45:04', 0, '2026-07-23 14:53:33.226095', 0, '2026-07-23 14:53:32.702387'),
(4, '101', 4, '1401', 'COMMUTER', NULL, 'OPERATING', 1, '2026-05-02 08:45:41', 0, '2026-07-23 14:53:33.226095', 0, '2026-07-23 14:53:32.75264');

-- ------------------------------------------------------------
-- 4. Table structure for equipments
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `equipments` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,                 -- 流水序
  `car_id` INTEGER NOT NULL,                               -- 車廂 ID
  `end_pos` INTEGER NOT NULL,                              -- 端點位置 (1端或2端)
  `equipment_name` VARCHAR(50) NOT NULL,                  -- 設備名稱
  `equipment_status` VARCHAR(50) NOT NULL,                -- 設備狀態
  `ip_address` VARCHAR(20) DEFAULT NULL,                   -- 網路位址
  `brand_model` VARCHAR(100) DEFAULT NULL,                 -- 廠牌型號
  `install_date` DATE DEFAULT NULL,                        -- 安裝日期
  `accumulated_hours` INTEGER DEFAULT 0,                   -- 累積運轉時數 (小時)
  `is_active` BOOLEAN NOT NULL DEFAULT 1,                  -- 是否合法/啟用 (1: 是, 0: 否)
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,-- 建立日期
  `created_by` INTEGER NOT NULL DEFAULT 0,                 -- 建立人員Seq
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,-- 異動日期
  `updated_by` INTEGER NOT NULL DEFAULT 0,                 -- 異動人員Seq
  `last_seen_at` DATETIME DEFAULT NULL,                    -- 最後通訊時間
  FOREIGN KEY (`car_id`) REFERENCES `cars` (`id`) ON UPDATE NO ACTION ON DELETE NO ACTION
);

-- ------------------------------------------------------------
-- 4. Initial Data for equipments
-- ------------------------------------------------------------
INSERT INTO `equipments` (
  `id`, `car_id`, `end_pos`, `equipment_name`, `equipment_status`,
  `ip_address`, `brand_model`, `install_date`, `accumulated_hours`, `is_active`,
  `created_at`, `created_by`, `updated_at`, `updated_by`, `last_seen_at`
) VALUES 
(1, 1, 1, 'PFC11011', 'OPERATING', '192.168.16.91', 'WAGO', '2026-07-01', 0, 1, '2026-07-20 23:07:27.510555', 0, '2026-07-23 14:47:13.241674', 0, '2026-07-23 14:47:13.1021'),
(2, 1, 2, 'PFC11012', 'OPERATING', '192.168.16.92', 'WAGO', '2026-07-01', 0, 1, '2026-07-20 23:07:27.510555', 0, '2026-07-23 14:47:13.241674', 0, '2026-07-23 14:47:13.091088'),
(3, 2, 1, 'PFC12011', 'OPERATING', '192.168.16.93', 'WAGO', '2026-07-01', 0, 1, '2026-07-20 23:07:27.510555', 0, '2026-07-23 14:48:53.227277', 0, '2026-07-23 14:48:52.328611'),
(4, 2, 2, 'PFC12012', 'OPERATING', '192.168.16.94', 'WAGO', '2026-07-01', 0, 1, '2026-07-20 23:07:27.510555', 0, '2026-07-23 14:48:53.227277', 0, '2026-07-23 14:48:52.646503'),
(5, 3, 1, 'PFC13011', 'OPERATING', '192.168.16.95', 'WAGO', '2026-07-01', 0, 1, '2026-07-20 23:07:27.510555', 0, '2026-07-23 14:49:13.223101', 0, '2026-07-23 14:49:12.227231'),
(6, 3, 2, 'PFC13012', 'OPERATING', '192.168.16.96', 'WAGO', '2026-07-01', 0, 1, '2026-07-20 23:07:27.510555', 0, '2026-07-23 14:49:13.223101', 0, '2026-07-23 14:49:12.796384'),
(7, 4, 1, 'PFC14011', 'OPERATING', '192.168.16.97', 'WAGO', '2026-07-01', 0, 1, '2026-07-20 23:07:27.510555', 0, '2026-07-23 14:49:23.233537', 0, '2026-07-23 14:49:22.553197'),
(8, 4, 2, 'PFC14012', 'OPERATING', '192.168.16.98', 'WAGO', '2026-07-01', 0, 1, '2026-07-20 23:07:27.510555', 0, '2026-07-23 14:49:23.233537', 0, '2026-07-23 14:49:22.462379');

-- ------------------------------------------------------------
-- 5. Table structure for sensors
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `sensors` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,                 -- 流水序
  `car_id` INTEGER NOT NULL,                               -- 所屬車廂
  `equipment_id` INTEGER DEFAULT NULL,                     -- 所屬設備
  `sensor_type` VARCHAR(50) NOT NULL,                      -- 感測器類型
  `sensor_code` VARCHAR(50) NOT NULL,                      -- 感測器編號
  `sensor_name` VARCHAR(50) NOT NULL,                      -- 感測器名稱
  `sensor_value` NUMERIC(10,2) NOT NULL,                   -- 感測器數值
  `sensor_unit` VARCHAR(10) NOT NULL,                      -- 感測器單位
  `sensor_status` VARCHAR(20) DEFAULT 'OPERATING',         -- 狀態
  `calibration_offset` NUMERIC(5,2) DEFAULT 0.00,         -- 校正偏移值
  `last_calibration_date` DATE DEFAULT NULL,               -- 最後校正日期
  `show_on_dashboard` BOOLEAN NOT NULL DEFAULT 1,          -- 是否顯示在儀表板
  `is_active` BOOLEAN NOT NULL DEFAULT 1,                  -- 是否合法/啟用
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,-- 建立日期
  `created_by` INTEGER NOT NULL DEFAULT 0,                 -- 建立人員Seq
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,-- 異動日期
  `updated_by` INTEGER NOT NULL DEFAULT 0,                 -- 異動人員Seq
  `save_history` BOOLEAN NOT NULL DEFAULT 1,               -- 是否記錄歷史紀錄
  FOREIGN KEY (`car_id`) REFERENCES `cars` (`id`) ON UPDATE NO ACTION ON DELETE NO ACTION,
  FOREIGN KEY (`equipment_id`) REFERENCES `equipments` (`id`) ON UPDATE NO ACTION ON DELETE NO ACTION
);

