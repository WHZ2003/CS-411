CREATE PROCEDURE RecommendProgramsForUser(
    IN p_user_id INT, IN p_max_tuition DECIMAL(12,2), IN p_min_salary DECIMAL(12,2)
)
BEGIN
    SELECT p.ProgramID,p.Name AS ProgramName,p.DegreeType,p.MedianSalary,
        p.UniversityID,u.Name AS UniversityName,u.Location,u.Tuition,
        p.MajorID,m.MajorName,p.Source,p.SourceKey,p.EarningsMetric,
        u.TuitionOutState,u.Website,m.CIPCode,
        (SELECT AVG(u2.Tuition) FROM Program p2
         JOIN University u2 ON p2.UniversityID=u2.UniversityID
         WHERE p2.MajorID=p.MajorID) AS AvgTuitionForMajor
    FROM Program p JOIN University u ON p.UniversityID=u.UniversityID
    JOIN Major m ON p.MajorID=m.MajorID
    WHERE p.MajorID=(SELECT PreferredMajor FROM User WHERE UserID=p_user_id)
        AND u.Tuition <= p_max_tuition AND p.MedianSalary >= p_min_salary
    ORDER BY p.MedianSalary DESC,p.ProgramID LIMIT 200;
END
