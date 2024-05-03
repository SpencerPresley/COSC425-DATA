# End of Semester TODO for the team.

## Backend
1. [ ] Export raw data in spreadsheet format to deliver to client.  
2. [ ] Finish auxillary stats
   - Total citations for category.
   - Total citations per paper per category. Needed for displaying most influential papers.
   - Total citation per author per category. Needed for displaying most influential faculty.
   - Average citations per paper per category.

3. [ ] Document code verbosely. 
   - [ ] Make a branch of the final main release and go through all the code you've been involved in and write abundant amounts of comments. I'm talking 2-3 comments per individual line. When we come back this will help immensely with getting back up to speed on how we implemented things.
   - [ ] Write general documentation of the code and how it's used and why it was written how it was.

## Frontend

### Core Features
- 1. [ ] Add theme data to category pages.
- 2. [x] Add department list to faculty page.
- 3. [ ] Pages need to be statically generated. They are currently making calls to the S3 bucket a ludicrous number of times.
- 4. [ ] Add most influential papers and faculty to category pages.
  - Limit display of each to 5 items.

### UI/UX

#### Features
- 1. [ ] SU colors for light and dark theme. We do not need to go crazy here. Just use a little bit of the maroon and a little bit of the gold on areas of the website which will not impede with readability or user experience. Use common sense.
- 2. [ ] Add modal popup for titles, when clicked popup will appear displaying that papers abstract.
  - A JSON file already exists which associates abstracts and titles.

#### Improvements | Must Have
- 1. [ ] Faculty and Article lists are unsorted on their respective pages. Sort them alphabetically.
- 2. [ ] Current styling of some pages leads to jarring color changes when toggling between light and dark mode. See a category page where when toggling to light mode the display box turns entirely black.
- 3. [ ] Add space between articles and faculty lists.
- 4. [ ] Clickable links need to be underlined and bolded. They should be highlighted in the SU Maroon color, or a lighter red color if SU Maroon impedes readability. On hover opacity should drop to add a darkening effect.

#### Improvements | Nice to Have
- 1. [ ] On category A-Z page, display under each category name smaller, italic, right-aligned text which displays a preview of the page via saying article and faculty count like so: Articles: 6, Faculty: 3.
- 2. [ ] Sticky category name on category pages.
  - [ ] When you click on a category and view its content, the category side nav container goes to the top of the list. As you dig down, you can no longer see the category listed you just selected (as in you click on history, then when you go down history is not on the side nav). Fixing this would be nice.
  - [ ] Have the side nav position stay relative to where its at so that if one is on the history page they see the history link in the side nav and the stuff above and below it. This would work with static pages, but current pages are dynamic. This may be solved indirectly when pages are made static.
  - [ ] Highlight the name of the category page you're on in the side nav. If I'm viewing math the math category should be bolded in the side nav.

#### Bug Fixes | Major
- 1. [ ] Fix the category A-Z pages from displaying the URL version of the category name to displaying the actual name.

#### Bug Fixes | Minor
- 1. [ ] When the faculty or article list is too long on the faculty/ article pages it creates a scrollbar inside the container. This leads to a scrollbar for the total window, a scrollbar for the side nav, and a scrollbar for the article / faculty content, leading to 3 scroll bars on one page.
    - See: Business -> Articles and Education and Educational Research -> Faculty
- 2. [ ] On the home page 'related' is spelled 'realted', fix this.

### Documentation
- 1. [ ] Document code verbosely. 
   - [ ] Make a branch of the final main release and go through all the code you've been involved in and write abundant amounts of comments. I'm talking 2-3 comments per individual line. When we come back this will help immensely with getting back up to speed on how we implemented things.
   - [ ] Write general documentation of the code and how it's used and why it was written how it was.

### Other | Only work on if everything else above this is done.
- 1. [ ] Investigate converting department names from their shortened WoS versions (i.e. 'Hist') to their full version (i.e. 'History').
- 2. [ ] REQUIRES BACKEND: Have chatgpt write a short 1-paragraph / 1-sentence generic definition of each category. Display this below the category title on the category page.

### Future | Not this semester
- 1. [ ] Add a color coding system associated with article counts to denote how "hot" a category is, thermometer like feature, and/or key word (i.e "Hot Topic", "Topic of Interest", "Topic of limited interest", "Obscure topic"). This would help the user better understand the relative strength of the concentration in a topic without needing to look it up on a sorted list.