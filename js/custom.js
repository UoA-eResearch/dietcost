$(document).ready(function() {
  function round(float) {
    return Math.round(float * 100) / 100;
  }
  function validate(min, max) {
    min = parseFloat(min);
    max = parseFloat(max);
    if (isNaN(min)) {
      return "Min must be a number";
    }
    if (isNaN(max)) {
      return "Max must be a number";
    }
    if (min > max) {
      return "Min must be less than max";
    }
    if (min < 0) {
      return "Min must be positive";
    }
    if (max < 0) {
      return "Max must be positive";
    }
    return "";
  }
  function createSlider(slider, name, machine_name, defaults) {
    var range = {'min': 0, 'max': defaults.max * 2} // range to choose from
    if (name.indexOf('%') !== -1) {
      range = {'min': 0, 'max': 100}
    }
    if (name == 'Energy kJ') {
      range = {'min': defaults.min * .9, 'max': defaults.max * 1.1}
    }
    noUiSlider.create(slider, {
      start: [defaults.min, defaults.max],
      connect: true,
      step: 1,
      behaviour: 'tap-drag',
      pips: {
        mode: 'count',
        values: 6,
        density: 4
      },
      range: range,
      format: {
        to: function(value) {
          return parseInt(value);
        },
        from: function(value) {
          return parseInt(value);
        }
      }
    });
    slider.noUiSlider.on('slide', function(values, handle) {
      // min handle = 0, max handle = 1
      if (handle) {
        $('#' + machine_name + ' input.max').val(values[handle]);
      } else {
        $('#' + machine_name + ' input.min').val(values[handle]);
      }
    });
    $('#' + machine_name + ' input.min').keyup(function() {
      slider.noUiSlider.set([$(this).val(), null]);
      var v = validate($(this).val(), $('#' + machine_name + ' input.max').val());
      this.setCustomValidity(v);
    });
    $('#' + machine_name + ' input.max').keyup(function() {
      slider.noUiSlider.set([null, $(this).val()]);
      var v = validate($('#' + machine_name + ' input.min').val(), $(this).val());
      this.setCustomValidity(v);
    });
  }
  $.get('get_nutrient_targets', function(data) {
    console.log(data);
    window.nutritional_targets = data;
    var keys = Object.keys(data).sort();
    for (var i in keys) {
      var person = keys[i];
      var selected = '';
      var fields = data[person];
      if (person == 'adult man') {
        selected = 'selected';
        $.each(fields, function(name, defaults) {
          var machine_name = name.replace(/[ %*]+/g, '_');
          var display_name = name.charAt(0).toUpperCase() + name.slice(1);
          if (name == 'CHO % energy') {
            display_name = 'Carbohydrates % energy';
          }
          if (name == 'Free sugars % energy*') {
            display_name = 'Total sugars % energy';
          }
          $("#dynamic_fields").append('<div id="' + machine_name + '" class="row"><p class="nt_label">' + display_name + '</p><div class="input-field col s2"><input name="nt_' + name + '_min" value="' + round(defaults.min) + '" type="text" class="min validate"><label for="min">Min</label></div><div class="slider-wrapper col s8"><div class="slider"></div></div><div class="input-field col s2"><input type="text" name="nt_' + name + '_max" value="' + round(defaults.max) + '" class="max validate"><label for="max">Max</label></div></div>');
          var slider = $('#' + machine_name + ' div.slider')[0];
          createSlider(slider, name, machine_name, defaults)
        });
      }
      var person_display = person.replace('7 girl', '7-year-old girl').replace('adult women', 'adult woman').replace('14 boy', '14-year-old boy');
      $('#person').append("<option " + selected + " value='" + person + "'>" + person_display + "</option>")
    }
    $('select').material_select();
    Materialize.updateTextFields();
    $('#person').change(function (e) {
      var p = $(this).val();
      var new_defaults = window.nutritional_targets[p];
      for (var name in new_defaults) {
        var defaults = new_defaults[name];
        if (!defaults) {
          console.error("No " + name + " nutritional constraint defined for " + p + "!");
          continue;
        }
        var machine_name = name.replace(/[ %*]+/g, '_');
        $("#dynamic_fields #" + machine_name + " input.min").val(round(defaults.min));
        $("#dynamic_fields #" + machine_name + " input.max").val(round(defaults.max));
        $("#dynamic_fields #" + machine_name + " input.min").trigger('keyup');
        $("#dynamic_fields #" + machine_name + " input.max").trigger('keyup');
        var slider = $("#dynamic_fields #" + machine_name + " div.slider")[0];
        slider.noUiSlider.destroy();
        createSlider(slider, name, machine_name, defaults)
      }
      for (var name in window.foodGroupTargets) {
        if (!window.foodGroupTargets[name]['constraints_serves']) continue;
        var machine_name = name.replace(/[ %*&]+/g, '_');
        var defaults = window.foodGroupTargets[name]['constraints_serves'][p];
        if (!defaults) {
          console.error("No " + name + " food group serves constraint defined for " + p + "!");
          continue;
        }
        $("#dynamic_fields #" + machine_name + " input.min").val(round(defaults.min));
        $("#dynamic_fields #" + machine_name + " input.max").val(round(defaults.max));
        $("#dynamic_fields #" + machine_name + " input.min").trigger('keyup');
        $("#dynamic_fields #" + machine_name + " input.max").trigger('keyup');
        var slider = $("#dynamic_fields #" + machine_name + " div.slider")[0];
        slider.noUiSlider.destroy();
        createSlider(slider, name, machine_name, defaults)
      }
    });
  });
  $.get('get_food_group_targets', function(data) {
    console.log(data);
    window.foodGroupTargets = data;
    $.each(data, function(name, constraints) {
      if (!constraints['constraints_serves']) return;
      var machine_name = name.replace(/[ %*&]+/g, '_');
      var display_name = name.charAt(0).toUpperCase() + name.slice(1) + ' serves';
      var defaults = constraints['constraints_serves']['adult man'];
      if (!defaults) {
        console.error("No " + name + " defined for adult man!");
        return;
      }
      $("#dynamic_fields").append('<div id="' + machine_name + '" class="row"><p class="nt_label">' + display_name + '</p><div class="input-field col s2"><input name="fg_' + name + '_min" value="' + round(defaults.min) + '" type="text" class="min validate"><label for="min">Min</label></div><div class="slider-wrapper col s8"><div class="slider"></div></div><div class="input-field col s2"><input type="text" name="fg_' + name + '_max" value="' + round(defaults.max) + '" class="max validate"><label for="max">Max</label></div></div>');
      var slider = $('#' + machine_name + ' div.slider')[0];
      createSlider(slider, name, machine_name, defaults)
    });
    Materialize.updateTextFields();
  });
  window.past_runs = {};
  $("#past_runs_content").on('click', '.past_run', function() {
    $(this).toggleClass('selected');
    var selected = $.map($(".past_run.selected"), function(n) {
      return n.id;
    });
    combined_stats = undefined;
    var count = 0;
    for (var i in selected) {
      var ts = selected[i];
      var s = past_runs[ts]['stats'];
      if (!s.total_meal_plans) continue;
      count++;
      if (!combined_stats) {
        combined_stats = JSON.parse(JSON.stringify(s)); // Deep copy to prevent clobbering
        continue;
      }
      combined_stats['total_meal_plans'] *= s.total_meal_plans;
      for (var k in s) {
        if (k == 'price' || k == 'variety') {
          combined_stats[k]['min'] += s[k]['min'];
          combined_stats[k]['max'] += s[k]['max'];
          combined_stats[k]['mean'] += s[k]['mean'];
        } else if (k == 'per_group') {
          for (var g in s[k]) {
            for (var measure in s[k][g]) {
              combined_stats[k][g][measure]['min'] += s[k][g][measure]['min'];
              combined_stats[k][g][measure]['max'] += s[k][g][measure]['max'];
              combined_stats[k][g][measure]['mean'] += s[k][g][measure]['mean'];
            }
          }
        }
      }   
    }
    if (count == 0) {
      $('#past_runs_stats').empty();
      return;
    }
    
    combined_stats['variety']['min'] /= count;
    combined_stats['variety']['max'] /= count;
    combined_stats['variety']['mean'] /= count;
    console.log(combined_stats);
    
    var fgSum = "";
    var keys = Object.keys(combined_stats.per_group).sort();
    for (var i in keys) {
      var k = keys[i];
      var d = combined_stats.per_group[k];
      fgSum += "<tr><td>" + k + "</td><td>" + round(d['amount']['min']) + "g-" + round(d['amount']['max']) + "g (" + round(d['amount']['mean']) + " avg)</td><td>$" + round(d['price']['min']) + "-$" + round(d['price']['max']) + " ($" + round(d['price']['mean']) + " avg)</td><td>" + round(d['serves']['min']) + "-" + round(d['serves']['max']) + " (" + round(d['serves']['mean']) + " avg)</td></tr>";
    }
    
    var foodGroupTable = "<h4>Food group breakdown</h4><br><table class='highlight bordered'><thead><tr><th>Category</th><th>Amount</th><th>Price</th><th>Serves</th></tr></thead>" + fgSum + "</table>";
    
    var priceInfo = 'Price range: $' + round(combined_stats['price']['min']) + ' - $' + round(combined_stats['price']['max']) + ' ($' + round(combined_stats['price']['mean']) + ' avg)';
    var varietyInfo = 'Variety range: ' + round(combined_stats['variety']['min']) + '-' + round(combined_stats['variety']['max']) + ' (' + round(combined_stats['variety']['mean']) + ' avg)';
    var html = "Total combined meal plans: " + combined_stats['total_meal_plans'] + '<br>' + priceInfo + '<br>' + varietyInfo + '<br><br>' + foodGroupTable;
    $('#past_runs_stats').html(html);
  });
  function get_meal_plans(variables) {
    $('#progress').show();
    $.ajax({
      url: 'get_meal_plans',
      type: "POST",
      data: JSON.stringify(variables),
      dataType: "json",
      contentType: "application/json",
      success: function(data) {
        $('#progress').hide();
        console.log(data);
        window.past_runs[data.timestamp] = data;
        var details = data.inputs.person + '<br>Iteration limit: '  + data.inputs.iteration_limit + '<br>Minimum serve size difference: ' + data.inputs.min_serve_size_difference + '<br>' + data.stats.total_meal_plans + ' results';
        var card = '<div class="col s12 m6"><div class="card past_run" id="' + data.timestamp + '"><div class="card-content"><span class="card-title">' + data.timestamp + '</span><p>' + details + '</p></div></div></div>';
        $('#past_runs_content').append(card);
        $('#meal_plans').empty();
        for (var hash in data.meal_plans) {
          var o = data.meal_plans[hash];
          var items = "";
          var keys = Object.keys(o.meal).sort();
          for (var i in keys) {
            var k = keys[i];
            var amount = o.meal[k];
            items += "<tr><td>" + k + "</td><td>" + round(amount) + "g</td></tr>";
          }
          var fgSum = "";
          var keys = Object.keys(o.per_group).sort();
          for (var i in keys) {
            var k = keys[i];
            var d = o.per_group[k];
            fgSum += "<tr><td>" + k + "</td><td>" + round(d['amount']) + "g</td><td>$" + round(d['price']) + "</td><td>" + round(d['serves']) + "</td></tr>";
          }
          var table = "<table class='highlight bordered'><thead><tr><th data-field='name'>Name</th><th data-field='amount'>Amount</th></tr></thead><tbody>" + items + "</tbody></table>";
          var collapsibleTable = "<ul class='collapsible' data-collapsible='accordion'><li><div class='collapsible-header'><i class='material-icons'>receipt</i>Items</div><div class='collapsible-body'>" + table + "</div></li></ul>";
          var foodGroupTable = "<h4>Food group breakdown</h4><br><table class='highlight bordered'><thead><tr><th>Category</th><th>Amount</th><th>Price</th><th>Serves</th></tr></thead>" + fgSum + "</table>";
          var summary = "<p class='price'>Price: $" + round(o.price) + "</p><p class='variety'>Variety: " + round(o.variety) + "</p>";
          var card = "<div class='col s12 m6'><div class='card hoverable'><div class='card-content'>" + table + "</div><div class='card-action'>" + foodGroupTable + "<br>" + summary + "</div></div></div>";
          $('#meal_plans').append(card);
        }
        $('.collapsible').collapsible();
        var summary = "Total meal plans: " + data.stats.total_meal_plans + ". ";
        if (data.stats.total_meal_plans) {
          summary += "Average price: $" + round(data.stats.price.mean) + ". Average variety: " + round(data.stats.variety.mean) + ". ";
        }
        summary += "<a href='" + data.csv_file + "' class='waves-effect waves-light btn download-as-csv' download><i class='material-icons left'>play_for_work</i>Download as csv</a>";
        $('#summary').html(summary);
      }
    });
  }
  get_meal_plans({person: 'adult man'});
  $('#nutritional_constraints').submit(function( e ) {
    e.preventDefault();
    var variables = {'nutrient_targets': {}, 'food_group_targets': {}}
    $(this).serializeArray().map(function(x){
      if (x.name == 'variety') {
        if (!variables['variety']) variables['variety'] = [];
        variables['variety'].push(parseInt(x.value));
      } else if (x.name.startsWith('nt_')) {
        var bits = x.name.split('_')
        var measure = bits[1];
        var minormax = bits[2];
        if (!variables['nutrient_targets'][measure]) variables['nutrient_targets'][measure] = {}
        variables['nutrient_targets'][measure][minormax] = parseFloat(x.value);
      } else if (x.name.startsWith('fg_')) {
        var bits = x.name.split('_');
        var measure = bits[1];
        var minormax = bits[2];
        if (!variables['food_group_targets'][measure]) variables['food_group_targets'][measure] = {}
        variables['food_group_targets'][measure][minormax] = parseFloat(x.value);
      } else {
        variables[x.name] = x.value;
      }
    });
    console.log(variables);
    get_meal_plans(variables);
  });
  $('.modal-trigger').leanModal();
});