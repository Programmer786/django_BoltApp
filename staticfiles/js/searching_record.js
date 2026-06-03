// <!-- the below code for employee searching -->

   $(document).ready(function(){
      $("#searchInput").on("keyup", function() {
         var value = $(this).val().toLowerCase();
         $(".employee-row").filter(function() {
               $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
         });
      });
   });

// <!-- the below code for project searching -->

   $(document).ready(function(){
      $("#searchInput").on("keyup", function() {
         var value = $(this).val().toLowerCase();
         $(".project-row").filter(function() {
               $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
         });
      });
   });

// <!-- the below code for expense searching -->

   $(document).ready(function(){
      $("#searchInput").on("keyup", function() {
         var value = $(this).val().toLowerCase();
         $(".expense-row").filter(function() {
               $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
         });
      });
   });

// <!-- the below code for asset searching -->

   $(document).ready(function(){
      $("#searchInput").on("keyup", function() {
         var value = $(this).val().toLowerCase();
         $(".asset-row").filter(function() {
               $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
         });
      });
   });

// <!-- the below code for district searching -->

$(document).ready(function(){
   $("#searchInput").on("keyup", function() {
      var value = $(this).val().toLowerCase();
      $(".district-row").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
      });
   });
});

// <!-- the below code for document searching -->

$(document).ready(function(){
   $("#searchInput").on("keyup", function() {
      var value = $(this).val().toLowerCase();
      $(".document-row").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
      });
   });
});

// <!-- the below code for education-document searching -->

$(document).ready(function(){
   $("#searchInput").on("keyup", function() {
      var value = $(this).val().toLowerCase();
      $(".education-document-row").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
      });
   });
});

// <!-- the below code for project-document searching -->

$(document).ready(function(){
   $("#searchInput").on("keyup", function() {
      var value = $(this).val().toLowerCase();
      $(".project-document-row").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
      });
   });
});


// <!-- the below code for tender-row searching -->

$(document).ready(function(){
   $("#searchInput").on("keyup", function() {
      var value = $(this).val().toLowerCase();
      $(".tender-row").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
      });
   });
});


// <!-- the below code for investor-row searching -->

$(document).ready(function(){
   $("#searchInput").on("keyup", function() {
      var value = $(this).val().toLowerCase();
      $(".investor-row").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
      });
   });
});
