CREATE TRIGGER IF NOT EXISTS salary_alert_trigger
AFTER INSERT ON Bookmark
WHEN (SELECT MedianSalary FROM Program WHERE ProgramID=NEW.ProgramID) < 60000
BEGIN
    INSERT INTO Alert(UserID,Message)
    SELECT NEW.UserID, 'Bookmarked program has reported median earnings below $60,000: ' || Name
    FROM Program WHERE ProgramID=NEW.ProgramID;
END;
