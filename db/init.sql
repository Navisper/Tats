CREATE TABLE IF NOT EXISTS animes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    genre VARCHAR(100),
    episodes INT
);
