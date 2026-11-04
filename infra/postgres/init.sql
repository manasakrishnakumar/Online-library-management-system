-- One database and one login per microservice (database-per-service).
-- Demo credentials only; real deployments would inject secrets.
CREATE USER bookuser PASSWORD 'book123';
CREATE DATABASE bookdb OWNER bookuser;
CREATE USER memberuser PASSWORD 'member123';
CREATE DATABASE memberdb OWNER memberuser;
CREATE USER lendinguser PASSWORD 'lending123';
CREATE DATABASE lendingdb OWNER lendinguser;
CREATE USER fineuser PASSWORD 'fine123';
CREATE DATABASE finedb OWNER fineuser;
CREATE USER notificationuser PASSWORD 'notification123';
CREATE DATABASE notificationdb OWNER notificationuser;
