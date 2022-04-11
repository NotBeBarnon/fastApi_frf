-- upgrade --
CREATE TABLE IF NOT EXISTS `user_user` (
    `user_number` INT NOT NULL PRIMARY KEY AUTO_INCREMENT COMMENT '用户编号',
    `uid` VARCHAR(10) NOT NULL UNIQUE COMMENT '用户UID，唯一标识用户',
    `username` VARCHAR(32) NOT NULL  COMMENT '用户名',
    `name` VARCHAR(32)   COMMENT '用户的名字',
    `family_name` VARCHAR(32)   COMMENT '用户的姓氏',
    `password` VARCHAR(64) NOT NULL  COMMENT '密码',
    `created_at` DATETIME(6) NOT NULL  COMMENT '创建时间' DEFAULT CURRENT_TIMESTAMP(6),
    `modified_at` DATETIME(6) NOT NULL  COMMENT '修改时间' DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户';
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(20) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4 COLLATE=utf8mb4_unicode_ci;
