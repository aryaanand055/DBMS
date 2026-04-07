CREATE DATABASE IF NOT EXISTS food_donation_db;
USE food_donation_db;

DROP TABLE IF EXISTS Feedback;
DROP TABLE IF EXISTS Delivery;
DROP TABLE IF EXISTS Requests;
DROP TABLE IF EXISTS Food_Donations;
DROP TABLE IF EXISTS Users;

CREATE TABLE Users (
    user_id    INT NOT NULL AUTO_INCREMENT,
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(100) NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    role       ENUM('donor','ngo','admin','receiver') NOT NULL,
    phone      VARCHAR(20) DEFAULT NULL,
    is_active  TINYINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id)
);

CREATE TABLE Food_Donations (
    donation_id  INT NOT NULL AUTO_INCREMENT,
    donor_id     INT NOT NULL,
    food_type    VARCHAR(100) NOT NULL,
    quantity     VARCHAR(100) NOT NULL,
    location     VARCHAR(255) NOT NULL,
    expiry_time  DATETIME NOT NULL,
    status       ENUM('pending','requested','accepted','in_transit','delivered','cancelled') NOT NULL DEFAULT 'pending',
    description  TEXT DEFAULT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (donation_id),
    CONSTRAINT fk_donation_donor FOREIGN KEY (donor_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE Requests (
    request_id       INT NOT NULL AUTO_INCREMENT,
    donation_id      INT NOT NULL,
    ngo_id           INT NOT NULL,
    delivery_address VARCHAR(255) DEFAULT NULL,
    request_status   ENUM('pending','accepted','rejected') NOT NULL DEFAULT 'pending',
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (request_id),
    CONSTRAINT fk_request_donation FOREIGN KEY (donation_id) REFERENCES Food_Donations(donation_id) ON DELETE CASCADE,
    CONSTRAINT fk_request_ngo FOREIGN KEY (ngo_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE Delivery (
    delivery_id     INT NOT NULL AUTO_INCREMENT,
    request_id      INT NOT NULL,
    delivery_status ENUM('pending','in_transit','delivered') NOT NULL DEFAULT 'pending',
    delivery_time   DATETIME DEFAULT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (delivery_id),
    CONSTRAINT fk_delivery_request FOREIGN KEY (request_id) REFERENCES Requests(request_id) ON DELETE CASCADE
);

CREATE TABLE Feedback (
    feedback_id INT NOT NULL AUTO_INCREMENT,
    user_id     INT NOT NULL,
    donation_id INT NOT NULL,
    rating      INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comments    TEXT DEFAULT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (feedback_id),
    CONSTRAINT fk_feedback_user FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_feedback_donation FOREIGN KEY (donation_id) REFERENCES Food_Donations(donation_id) ON DELETE CASCADE
);
