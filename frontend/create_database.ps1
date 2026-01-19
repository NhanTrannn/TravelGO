# Script tao database cho SQL Server
Write-Host "Tao database nlp_travel_db..." -ForegroundColor Cyan

$query = @"
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'nlp_travel_db')
BEGIN
    CREATE DATABASE nlp_travel_db;
    PRINT 'Database created successfully';
END
ELSE
BEGIN
    PRINT 'Database already exists';
END
GO

USE nlp_travel_db;
GO

-- Grant permissions cho prisma_user
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'prisma_user')
BEGIN
    CREATE USER prisma_user FOR LOGIN prisma_user;
END
GO

ALTER ROLE db_owner ADD MEMBER prisma_user;
GO

PRINT 'Permissions granted to prisma_user';
GO
"@

# Luu query vao file
$query | Out-File -FilePath "create_database.sql" -Encoding UTF8

Write-Host ""
Write-Host "File create_database.sql da duoc tao!" -ForegroundColor Green
Write-Host ""
Write-Host "Cach 1: Chay voi sqlcmd" -ForegroundColor Yellow
Write-Host "  sqlcmd -S localhost\SQLEXPRESS -U sa -P YourSaPassword -i create_database.sql" -ForegroundColor White
Write-Host ""
Write-Host "Cach 2: Chay trong SQL Server Management Studio" -ForegroundColor Yellow
Write-Host "  1. Mo SSMS" -ForegroundColor White
Write-Host "  2. Connect voi sa account" -ForegroundColor White
Write-Host "  3. Mo file create_database.sql" -ForegroundColor White
Write-Host "  4. Execute (F5)" -ForegroundColor White
Write-Host ""
