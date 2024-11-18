from pydantic import BaseModel
from typing import Dict


class Abstract(BaseModel):
    abstract: str
    doi: str


# Key = DOI, Value = Abstract
doi_to_abstract_dict: Dict[str, str] = {}

# this is in the data
abstract_1 = Abstract(
    abstract="Drawing on expectation states theory and expertise utilization literature, we examine the effects of team members' actual expertise and social status on the degree of influence they exert over team processes via perceived expertise. We also explore the conditions under which teams rely on perceived expertise versus social status in determining influence relationships in teams. To do so, we present a contingency model in which the salience of expertise and social status depends on the types of intragroup conflicts. Using multiwave survey data from 50 student project teams with 320 members at a large national research institute located in South Korea, we found that both actual expertise and social status had direct and indirect effects on member influence through perceived expertise. Furthermore, perceived expertise at the early stage of team projects is driven by social status, whereas perceived expertise at the later stage of a team project is mainly driven by actual expertise. Finally, we found that members who are being perceived as experts are more influential when task conflict is high or when relationship conflict is low. We discuss the implications of these findings for research and practice.",
    doi="10.1177/1059601117728145",
)
doi_to_abstract_dict[abstract_1.doi] = abstract_1.abstract

# # this is not in the data
# abstract_2 = Abstract(
#     abstract="The goal of this paper is to investigate how deregulating foreign equity ownership influences a firm's innovation investment. We attempt to answer this question using data from 530 Korean manufacturing firms between 1998 and 2003 through generalised estimating equations. Our findings suggest that foreign ownership and R&D investment exhibit an inverted U-shaped relationship because the incentives to monitor managers' decision-making processes initially play a greater role, but this role stagnates as the share owned by foreign investors becomes concentrated. In addition, we consider firm heterogeneity and observe the negative moderation effects of firm age and the positive moderation effects of growth opportunity.",
#     doi="10.1080/09537325.2021.1991572"
# )
# doi_to_abstract_dict[abstract_2.doi] = abstract_2.abstract

# # this is in the data
# abstract_3 = Abstract(
#     abstract="This study examined the role of perceived organizational commitment on managers' assessments of employees' career growth opportunities. Based on a paired sample of 161 legal secretaries and their managers, results indicated that managers used the attitudes and behaviors displayed by employees (strong extra-role performance and enhanced work engagement) as cues from which to base their perceptions of employees' affective commitment to the organization. In turn, employees perceived as highly committed to the organization experienced enhanced content and structural career growth opportunities. Moreover, the relation between managers' perceptions of employees' organizational commitment and content career growth opportunities was stronger for employees perceived as also highly committed to their careers than for employees perceived as less committed to their careers.",
#     doi="10.1177/0894845317714892"
# )
# doi_to_abstract_dict[abstract_3.doi] = abstract_3.abstract

# # this is in the data
# abstract_4 = Abstract(
#     abstract="This study examined how firms combine alliances and acquisitions in an exploration/exploitation framework. By conducting cluster analysis on a sample of 1270 acquisitions made by 836 firms, we first identified the patterns in alliance and acquisition activities undertaken by these firms. Five distinct patterns were identified: (I) low alliance-low acquisition, (II) low alliance-high acquisition, (III) high alliance-low acquisition, (IV) high alliance-high acquisition, and (V) medium alliance-very high acquisition. Next, we analyzed the different ways in which the two modes were interlinked within these five patterns for exploration/exploitation. Patterns III and IV appeared to involve both exploration/exploitation and mutually reinforce exploration/exploitation. In contrast, in the remaining patterns, the two modes appeared to be more loosely coupled with each other, with a focus on exploitation.",
#     doi="10.1177/03063070221129452"
# )
# doi_to_abstract_dict[abstract_4.doi] = abstract_4.abstract
