  // Function to fetch districts based on selected province
  function getDistrictsByProvince(provinceName) {
      $.ajax({
        url: "/get-districts",
        data: { province_name: provinceName },
        success: function (districts) {
          var districtDropdown = $("#district-dropdown");
          districtDropdown.empty();
          districtDropdown.append("<option value=''>Select District</option>");
          $.each(districts, function (key, value) {
            districtDropdown.append("<option value='" + value.id + "'>" + value.name + "</option>"); // date sent to html
          });
        },
        error: function (xhr, status, error) {
          console.error(error);
        },
      });
    }


  // Function to fetch districts based on selected province second
  function getDistrictsByProvinceSecond(provinceName) {
    $.ajax({
      url: "/get-districts",
      data: { province_name: provinceName },
      success: function (districts) {
        var districtDropdown = $("#district-second-dropdown");
        districtDropdown.empty();
        districtDropdown.append("<option value=''>Select District</option>");
        $.each(districts, function (key, value) {
          districtDropdown.append("<option value='" + value.id + "'>" + value.name + "</option>"); // date sent to html
        });
      },
      error: function (xhr, status, error) {
        console.error(error);
      },
    });
  }


  // Event listener for province dropdown change for first
  $("#province-dropdown").change(function () {
    //var province_name = $(this).find("option:selected").text(); //this for using str value
    var province_name = $(this).val();  //this for using int value
    if (province_name && province_name !== "None") {
      getDistrictsByProvince(province_name);
    } else {
      // If no province is selected, clear the districts and tehsils dropdowns
      $("#district-dropdown").empty();
      $("#district-dropdown").append("<option value=''>Select District</option>");
    }
  });

  // Event listener for province dropdown change for second
  $("#province-second-dropdown").change(function () {
    //var province_name = $(this).find("option:selected").text(); //this for using str value
    var province_name = $(this).val();  //this for using int value
    if (province_name && province_name !== "None") {
      getDistrictsByProvinceSecond(province_name);
    } else {
      // If no province is selected, clear the districts and tehsils dropdowns
      $("#district-second-dropdown").empty();
      $("#district-second-dropdown").append("<option value=''>Select District</option>");
    }
  });

  // Event listener for district dropdown change for LQAS
  $("#district-dropdown").change(function () {
    //var district_name = $(this).find("option:selected").text();  //this for using str value
    var district_name = $(this).val();  //this for using int value
    if (district_name && district_name !== "None") {
      getTehsilsByDistrictLQAS(district_name);
    } else {
      // If no district is selected, clear the tehsils dropdown
      $("#tehsil-dropdown-lqas").empty();
      $("#tehsil-dropdown-lqas").append("<option value=''>Select Tehsil</option>");
    }
  });

  // Event listener for district dropdown change for LQAS
  $("#district-second-dropdown").change(function () {
    //var district_name = $(this).find("option:selected").text();  //this for using str value
    var district_name = $(this).val();  //this for using int value
    if (district_name && district_name !== "None") {
      getTehsilsByDistrictLQAS(district_name);
    } else {
      // If no district is selected, clear the tehsils dropdown
      $("#tehsil-dropdown-lqas").empty();
      $("#tehsil-dropdown-lqas").append("<option value=''>Select Tehsil</option>");
    }
  });

  // Event listener for tehsil dropdown change for LQAS
  $("#tehsil-dropdown-lqas").change(function () {
    var tehsil_name = $(this).val();
    if (tehsil_name && tehsil_name !== "None") {
      getUnionCouncilsByTehsilLQAS(tehsil_name);
    } else {
      // If no tehsil is selected, clear the union council dropdown
      $("#union-council-dropdown").empty();
      $("#union-council-dropdown").append("<option value=''>Select Union Council</option>");
    }
  });

  // Event listener for union council dropdown change for LQAS
  $("#union_council-dropdown_lqas").change(function () {
    var union_council_name = $(this).val();
    if (union_council_name && union_council_name !== "None") {
      getUnionCouncilCode(union_council_name);
    } else {
      // If no union council is selected, clear the textbox
      $("#union_council_code-textbox").val("");
    }
  });

 


// ----------------------------------------Below for PCM add_cluster_pcm---------------------------------------------------

// Function to fetch tehsils based on selected district 
function getTehsilsByDistrictPCM(districtName) {
  $.ajax({
    url: "/get-tehsils",
    data: { district_name: districtName },
    success: function (tehsils) {
      var tehsilDropdown = $("#tehsil-dropdown-pcm");
      tehsilDropdown.empty();
      tehsilDropdown.append("<option value=''>Select Tehsil</option>");
      $.each(tehsils, function (key, value) {
        tehsilDropdown.append("<option value='" + value.name + "'>" + value.name + "</option>"); // date sent to html
      });
    },
    error: function (xhr, status, error) {
      console.error(error);
    },
  });
}

// Function to fetch union councils based on selected tehsil for PCM
function getUnionCouncilsByTehsilPCM(tehsilName) {
  $.ajax({
    url: "/get-union-councils-pcm",
    data: { tehsil_name: tehsilName },
    success: function (unionCouncils) {
      var unionCouncilDropdown = $("#union_council-dropdown_pcm");
      unionCouncilDropdown.empty();
      unionCouncilDropdown.append("<option value=''>Select Union Council</option>");
      $.each(unionCouncils, function (key, value) {
        unionCouncilDropdown.append("<option value='" + value.name + "'>" + value.name + "</option>");
      });
    },
    error: function (xhr, status, error) {
      console.error(error);
    },
  });
}  

// Event listener for district dropdown change for PCM
$("#district-dropdown").change(function () {
  //var district_name = $(this).find("option:selected").text();  //this for using str value
  var district_name = $(this).val();  //this for using int value
  if (district_name && district_name !== "None") {
    getTehsilsByDistrictPCM(district_name);
  } else {
    // If no district is selected, clear the tehsils dropdown
    $("#tehsil-dropdown-pcm").empty();
    $("#tehsil-dropdown-pcm").append("<option value=''>Select Tehsil</option>");
  }
});

 // Event listener for tehsil dropdown change for PCM
 $("#tehsil-dropdown-pcm").change(function () {
  var tehsil_name = $(this).val();
  if (tehsil_name && tehsil_name !== "None") {
    getUnionCouncilsByTehsilPCM(tehsil_name);
  } else {
    // If no tehsil is selected, clear the union council dropdown
    $("#union-council-dropdown").empty();
    $("#union-council-dropdown").append("<option value=''>Select Union Council</option>");
  }
});

  // Event listener for union council dropdown change for PCM
  $("#union_council-dropdown_pcm").change(function () {
  var union_council_name = $(this).val();
  if (union_council_name && union_council_name !== "None") {
    getUnionCouncilCode(union_council_name);
  } else {
    // If no union council is selected, clear the textbox
    $("#union_council_code-textbox").val("");
  }
});