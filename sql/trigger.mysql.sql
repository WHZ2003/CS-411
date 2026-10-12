CREATE TRIGGER salary_alert_trigger AFTER INSERT ON Bookmark FOR EACH ROW
BEGIN
    INSERT INTO Alert(UserID,Message)
    SELECT NEW.UserID,
        CONCAT('Bookmarked program has reported median earnings below $60,000: ', Name)
    FROM Program WHERE ProgramID=NEW.ProgramID AND MedianSalary < 60000;
END
