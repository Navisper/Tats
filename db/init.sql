-- Railway PostgreSQL Database Initialization Script
-- This script sets up the anime database schema for Railway deployment

-- Enable UUID extension for potential future use
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create animes table with enhanced constraints and indexing
CREATE TABLE IF NOT EXISTS animes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    genre VARCHAR(100),
    episodes INTEGER CHECK (episodes > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_animes_title ON animes(title);
CREATE INDEX IF NOT EXISTS idx_animes_genre ON animes(genre);
CREATE INDEX IF NOT EXISTS idx_animes_created_at ON animes(created_at);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at on row updates
DROP TRIGGER IF EXISTS update_animes_updated_at ON animes;
CREATE TRIGGER update_animes_updated_at
    BEFORE UPDATE ON animes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data if table is empty (for initial setup)
INSERT INTO animes (title, genre, episodes)
SELECT * FROM (VALUES
    ('Fullmetal Alchemist: Brotherhood', 'Action, Adventure', 64),
    ('Demon Slayer', 'Action, Fantasy', 26),
    ('Your Name', 'Romance, Drama', 1),
    ('Attack on Titan', 'Action, Drama', 75),
    ('One Piece', 'Adventure, Comedy', 1000),
    ('Naruto', 'Action, Adventure', 720)
) AS sample_data(title, genre, episodes)
WHERE NOT EXISTS (SELECT 1 FROM animes LIMIT 1);

-- Create a view for anime statistics (optional, for reporting)
CREATE OR REPLACE VIEW anime_stats AS
SELECT 
    COUNT(*) as total_animes,
    AVG(episodes) as avg_episodes,
    MAX(episodes) as max_episodes,
    MIN(episodes) as min_episodes,
    COUNT(DISTINCT genre) as unique_genres
FROM animes;

-- Grant necessary permissions (Railway handles most permissions automatically)
-- These are mainly for documentation and explicit permission management
GRANT SELECT, INSERT, UPDATE, DELETE ON animes TO CURRENT_USER;
GRANT USAGE, SELECT ON SEQUENCE animes_id_seq TO CURRENT_USER;
GRANT SELECT ON anime_stats TO CURRENT_USER;
