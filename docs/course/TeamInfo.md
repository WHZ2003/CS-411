# team050-Hajimi

## Basic Information

|   Info      |        Description     |
| ----------- | ---------------------- |
| TeamID      |        Team-050        |
| TeamName    |         Hajimi         |
| Captain     |       Wenhao Zhang     |
| Captain     |  wenhaoz5@illinois.edu |
| Member1     |        Yuhui Liu       |
| Member1     |   yuhuil4@illinois.edu |
| Member2     |     Tianxiang Wu       |
| Member2     |  tw50@illinois.edu     |
| Member3     |       Zixuan Huang     |
| Member3     | zixuan23@illinois.edu  |

## Project Information

|   Info      |        Description                                    |
| ----------- | ----------------------------------------------------- |
|  Title      |      College Employment & Salary Analysis Platform    |
| System URL  |      link_to_system                                   |
| Video Link  |      link_to_video                                    |


Project Summary:
Every student needs to make a crucial decision, choosing which university to attend and which major to take when they enter university. However, the current rankings for universities and majors do not focus on employment rates and post-graduation salaries. In our project, we will construct a website to address this problem. This website integrates the real-world datasets:  the U.S. Department of Education’s College Scorecard (tuition, majors, and alumni salaries) with job and salary data from Kaggle/Glassdoor.

Detailed description:
Our website aims to help students choose their universities and majors. For now, students have trouble evaluating the benefits and costs of entering college. By comparing the cost of receiving a college education and the graduate outcomes, our website will answer the following question:
What are the typical salaries for graduates after taking a specific major?
Which universities deliver the best ROI(return on investment) for the specific major?
How do different institutions compare regionally or nationally?

Usefulness:
Our project will provide high school students, their parents, and counselors with a tool to evaluate the university. Though some websites like the College Scoreboard official website, they only provide raw data and are not friendly for students and their parents (format is hard to read). In our project, we will integrate multiple datasets. Moreover, it will focus on ROI and employment rate instead of general rankings (U.S. News).

Realness:
We will use real, publicly available datasets:
U.S. Department of Education- College ScoreBoard
	Size:Thousands of universities and programs across the U.S.
	Content: Tuition, graduation rate, debt levels, alumni median earnings, majors offered.
Job/Salary Data from Kaggle or Glassdoor:
	Size:At least 50,000+ job postings/salary entries.
	Content: Company names, job roles, average salaries, location.

By integrating these datasets, we can use the cost of education (tuition, major) related to graduate outcomes (average salary, jobs). Also, each dataset is sufficiently large, which ensures that it meets the project requirements.

Functionality:
1.Search&View: Users can search for a university or major and view salary/employment outcomes.
	2.Compare: Users can select multiple universities or majors for side-by-side ROI comparison.
	3.Filter: Users can filter results by region, tuition range, or field of study.
	4. User Accounts: Students can create accounts, save comparisons, and bookmark schools/majors.
Create: Users create accounts, save comparisons, bookmark universities.
Read: Browse/search/filter universities and majors.
Update: Users update their saved comparisons or account info.
Delete: Users delete saved comparisons or bookmarks.

Creative Functionality:
Our creative component is Dynamic Salary Distribution Table. In the detail page of schools or majors, the user can not only see the average salary of students, but also view detailed salary distribution by choosing different graduation periods, for example, after 1-year, 5-year or 10-year graduation. The table will directly show the salary distribution based on this filter. In this way, the students and parents can estimate their expected salary after graduation, and gain a deeper understanding of how salaries change over time and the differences across various stages. This visualization function is more powerful than directly presenting the numbers.

Low-Fidelity UI Mockup:
Homepage: The homepage provides a search bar at the top where users can type a school or major to search for. A filter button on the left expands advanced filtering options, including school name, major, and salary range (min–max). A search button on the right executes the query.

University / Major Detail Page: After search for a university/major. This page will be displayed. This page displays detailed statistics for a specific school and major, including tuition, graduation rate, and median salary. A visualization chart (e.g., histogram or distribution plot) shows salary levels with interactive cursor functionality to view percentages. At the top, users can navigate back to the homepage or select the program to add to a comparison.

Comparison Dashboard: The comparison page allows users to select two schools/majors side by side. For each program, tuition, graduation rate, and salary data are shown in a structured column layout. Simple charts below provide quick visual comparisons. A button at the top lets users save the comparison to their account for future reference, a navigation button goes to the comparison board, and another navigation button returns to the homepage. This page emphasizes ROI comparison across institutions.

User Account Page
Bookmarks & Saved Comparisons: Users can view saved schools, majors, or comparisons. Each entry lists details (school, major, salary, grad rate) with delete buttons on the right for removing items.
Account Settings: Users can edit personal details such as username, email, preferred school/major, and job interests.


Collaboration Details:
We divide our tasks into four main categories, which includes data processing, backend development, front-end development, data analysis & visualization, function augmentation and project management.
Our team leader Wenhao Zhang will be responsible for managing the whole project as well as keeping the documents updated.
Other responsibilities are as follows:
Yuhui Liu will be responsible for data processing, which includes collecting, cleansing and organizing data. Yuhui will also build the database.
Tianxiang Wu will be responsible for the backend development, mainly focusing on building the system and API. The goal is to realize the main functionality of the platform.
Zixuan Huang will be responsible for data analysis & visualization. He will calculate metrics such as ROI and employment rates, and present results through charts and visualization tools.
Wenhao Zhang will be responsible for frontend development, which includes designing and implementing the user interface, supporting search, filtering and account functions.
If we have additional time available, our team members will discuss and determine the feasibility of adding other features. We will decide whether to proceed with this based on our current progress.
